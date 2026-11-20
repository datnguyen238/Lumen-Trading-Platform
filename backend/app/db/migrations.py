"""Idempotent additive migration for currency-aware quotes and wallets."""
from sqlalchemy import inspect, text, update

FX_COLUMNS = {'native_currency': 'VARCHAR(8)', 'fx_rate': 'NUMERIC(30,18) NOT NULL DEFAULT 1',
              'fx_timestamp': 'TIMESTAMP', 'fx_source': "VARCHAR(64) NOT NULL DEFAULT 'same_currency'"}
CURRENCY_COLUMNS = {'accounts': {'currency'}, 'symbols': {'currency', 'exchange'}, 'price_bars': {'currency'},
                   **{table: set(FX_COLUMNS) for table in ('orders', 'trades', 'order_previews', 'execution_details')},
                   'trades': set(FX_COLUMNS) | {'account_value'}, 'execution_details': set(FX_COLUMNS) | {'account_value'}}


def missing_currency_columns(connection):
    schema = inspect(connection)
    tables = set(schema.get_table_names())
    missing = [f'{table}.{column}' for table, columns in CURRENCY_COLUMNS.items()
               for column in columns - ({item['name'] for item in schema.get_columns(table)} if table in tables else set())]
    if connection.dialect.name == 'postgresql' and 'positions' in tables:
        average = next(item for item in schema.get_columns('positions') if item['name'] == 'average_price')
        if (getattr(average['type'], 'scale', 0) or 0) < 14:
            missing.append('positions.average_price_precision')
    return missing


def migrate_currencies(engine):
    from app.models.models import Symbol, PriceBar
    from app.services.currencies import LEGACY_US_SYMBOLS
    additions = {
        'accounts': {'currency': "VARCHAR(3) NOT NULL DEFAULT 'USD'"},
        'symbols': {'currency': 'VARCHAR(8)', 'exchange': 'VARCHAR(64)'},
        'price_bars': {'currency': 'VARCHAR(8)'},
        **{table: dict(FX_COLUMNS) for table in ('orders', 'trades', 'order_previews', 'execution_details')},
        'trades': {**FX_COLUMNS, 'account_value': 'NUMERIC(24,4)'},
        'execution_details': {**FX_COLUMNS, 'account_value': 'NUMERIC(24,4)'},
    }
    with engine.begin() as connection:
        tables = set(inspect(connection).get_table_names())
        for table, columns in additions.items():
            if table not in tables:
                continue
            existing = {column['name'] for column in inspect(connection).get_columns(table)}
            for column, declaration in columns.items():
                if column not in existing:
                    connection.execute(text(f'ALTER TABLE {table} ADD COLUMN {column} {declaration}'))
        if connection.dialect.name == 'postgresql' and 'positions' in tables:
            average = next(item for item in inspect(connection).get_columns('positions') if item['name'] == 'average_price')
            if (getattr(average['type'], 'scale', 0) or 0) < 14:
                # Widen precision only; legacy balances and cost values do not change.
                connection.execute(text('ALTER TABLE positions ALTER COLUMN average_price TYPE NUMERIC(30,14)'))
        # Only the established US starter catalog has a verified legacy USD unit.
        # Unknown legacy instruments stay unclassified until a provider refresh.
        for model in (Symbol, PriceBar):
            if model.__tablename__ in tables:
                connection.execute(update(model).where(model.symbol.in_(LEGACY_US_SYMBOLS), model.currency.is_(None)).values(currency='USD'))
