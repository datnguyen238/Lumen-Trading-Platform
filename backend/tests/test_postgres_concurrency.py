from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from decimal import Decimal
from threading import Barrier
import pytest
from sqlalchemy.orm import sessionmaker
from app.models.models import Account, Order, PriceBar, Trade
from app.models.enums import OrderSide, OrderStatus, OrderType
from app.schemas.orders import OrderCreate, PreviewRequest
from app.services.execution import execute_market_order, place_order, cancel_order, process_pending_limit_orders
from app.services.order_preview import create_preview, confirm_preview


def parallel(db, work):
    if db.get_bind().dialect.name != 'postgresql':
        pytest.skip('Requires isolated PostgreSQL: set TEST_POSTGRES_URL')
    factory = sessionmaker(bind=db.get_bind(), autoflush=False, expire_on_commit=False)
    barrier = Barrier(2)
    def run(i):
        with factory() as connection:
            barrier.wait(timeout=5)
            try:
                return work(connection, i)
            except ValueError:
                connection.rollback()
                return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        return list(pool.map(run, range(2)))


def test_two_concurrent_buys_cannot_spend_same_cash(db_session, account_with_price):
    account_id = account_with_price.id
    def buy(db, i):
        return execute_market_order(db, OrderCreate(account_id=account_id, symbol='AAPL', side='BUY', quantity=60, client_order_id=f'concurrent-order-{i:04}')).id
    results = parallel(db_session, buy)
    assert sum(result is not None for result in results) == 1
    db_session.expire_all()
    assert db_session.get(Account, account_id).cash_balance == 4000
    assert db_session.query(Trade).count() == 1


def test_concurrent_confirmations_create_one_fill(db_session, account_with_price):
    preview = create_preview(db_session, PreviewRequest(account_id=account_with_price.id, symbol='AAPL', side='BUY', notional=250))
    results = parallel(db_session, lambda db, i: confirm_preview(db, preview.id, preview.account_id).id)
    assert results[0] == results[1] and results[0] is not None
    assert db_session.query(Trade).count() == 1
    db_session.expire_all()
    assert db_session.get(Account, preview.account_id).cash_balance == 9750


def test_cancellation_racing_a_fill_has_one_terminal_result(db_session, account_with_price):
    account_id = account_with_price.id
    order = place_order(db_session, OrderCreate(account_id=account_id, symbol='AAPL', side='BUY', quantity=2, order_type='LIMIT', limit_price=90))
    order_id = order.id
    db_session.add(PriceBar(symbol='AAPL', timestamp=datetime.utcnow()+timedelta(seconds=1), open=80, high=80, low=80, close=80)); db_session.commit()
    def act(db, i):
        if i == 0:
            return process_pending_limit_orders(db, account_id=account_id)
        return cancel_order(db, order_id, account_id).status
    parallel(db_session, act)
    db_session.expire_all()
    final = db_session.get(Order, order_id)
    assert final.status in (OrderStatus.CANCELED, OrderStatus.FILLED)
    expected = 1 if final.status == OrderStatus.FILLED else 0
    assert db_session.query(Trade).count() == expected
    assert db_session.get(Account, account_id).cash_balance == (9840 if expected else 10000)


def test_private_tables_are_inaccessible_to_supabase_browser_roles(db_session, account_with_price):
    from sqlalchemy import text
    from app.db.privacy import protect_private_tables, PRIVATE_TABLES
    engine = db_session.get_bind()
    if engine.dialect.name != 'postgresql':
        pytest.skip('Requires isolated PostgreSQL')
    db_session.commit()  # Release fixture SELECT locks before exercising schema privacy DDL.
    with engine.begin() as connection:
        for role in ('anon', 'authenticated'):
            if not connection.execute(text('SELECT 1 FROM pg_roles WHERE rolname=:role'), {'role': role}).first():
                connection.execute(text(f'CREATE ROLE "{role}" NOLOGIN'))
            connection.execute(text(f'GRANT SELECT ON accounts TO "{role}"'))
    protect_private_tables(engine)
    with engine.connect() as connection:
        for table in PRIVATE_TABLES:
            assert connection.execute(text("SELECT relrowsecurity FROM pg_class WHERE oid=to_regclass(:name)"), {'name': table}).scalar() is True
        for role in ('anon', 'authenticated'):
            assert connection.execute(text("SELECT has_table_privilege(:role, 'accounts', 'SELECT')"), {'role': role}).scalar() is False
    assert db_session.query(Account).count() == 1  # Trusted backend owner retains access.
