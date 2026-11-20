"""Idempotent additive migration for currency-aware quotes and wallets."""
from sqlalchemy import inspect, text, update

CURRENCY_COLUMNS = {'accounts': {'currency'}, 'symbols': {'currency', 'exchange'}, 'price_bars': {'currency'}}


def missing_currency_columns(connection):
    schema = inspect(connection)
    tables = set(schema.get_table_names())
    return [f'{table}.{column}' for table, columns in CURRENCY_COLUMNS.items()
            for column in columns - ({item['name'] for item in schema.get_columns(table)} if table in tables else set())]


def migrate_currencies(engine):
    from app.models.models import Symbol, PriceBar
    from app.services.currencies import LEGACY_US_SYMBOLS
    additions = {
        'accounts': {'currency': "VARCHAR(3) NOT NULL DEFAULT 'USD'"},
        'symbols': {'currency': 'VARCHAR(8)', 'exchange': 'VARCHAR(64)'},
        'price_bars': {'currency': 'VARCHAR(8)'},
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
        # Only the established US starter catalog has a verified legacy USD unit.
        # Unknown legacy instruments stay unclassified until a provider refresh.
        for model in (Symbol, PriceBar):
            if model.__tablename__ in tables:
                connection.execute(update(model).where(model.symbol.in_(LEGACY_US_SYMBOLS), model.currency.is_(None)).values(currency='USD'))
