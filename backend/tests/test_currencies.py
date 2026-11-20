from datetime import datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import text

from app.db.migrations import migrate_currencies, missing_currency_columns
from app.models.models import Account, Order, OrderPreview, Position, PriceBar, Symbol, Trade
from app.models.enums import OrderSide, OrderType, OrderStatus
from app.services.execution import process_pending_limit_orders
from app.services.price_refresh import _upsert_bar
from app.services import symbol_search
from test_auth_trading_api import signup


def vnd_signup(client):
    response = client.post('/auth/signup', json={'email': 'vietnam@example.com', 'full_name': 'Vietnam trader',
        'password': 'practice123', 'currency': 'VND'})
    assert response.status_code == 200, response.text
    data = response.json()
    client.headers['X-CSRF-Token'] = data['csrf_token']
    return data


def quote(db, price=52000, currency='VND', symbol='VNM.VN', when=None):
    bar = _upsert_bar(db, symbol, when or datetime.utcnow(), price, price, price, price, 1000, currency=currency)
    db.commit()
    return bar


def preview(client, account_id, **kwargs):
    return client.post('/orders/preview', json={'account_id': account_id, 'symbol': 'VNM.VN', 'side': 'BUY', **kwargs})


def confirm(client, response):
    assert response.status_code == 200, response.text
    result = client.post('/orders/confirm', json={'preview_id': response.json()['id']})
    assert result.status_code == 200, result.text
    return result.json()


def test_currency_portfolios_are_independent_and_survive_login(client, db_session):
    data = vnd_signup(client)
    vnd = data['accounts'][0]
    assert vnd['currency'] == 'VND' and Decimal(vnd['cash_balance']) == 1000000000
    created = client.post('/accounts/', json={'user_id': data['user']['id'], 'name': 'US stocks', 'currency': 'USD'})
    assert created.status_code == 200, created.text
    usd = created.json()
    assert usd['currency'] == 'USD' and Decimal(usd['cash_balance']) == 100000
    assert client.post('/accounts/', json={'user_id': data['user']['id'], 'name': 'Invalid', 'currency': 'EUR'}).status_code == 422
    # Currency is immutable; no update route can relabel existing balances.
    assert client.patch(f"/accounts/{vnd['id']}", json={'currency': 'USD'}).status_code in (404, 405)
    assert client.post('/auth/logout', json={}).status_code == 200
    logged = client.post('/auth/login', json={'email': 'vietnam@example.com', 'password': 'practice123'}).json()
    assert {item['currency'] for item in logged['accounts']} == {'USD', 'VND'}


def test_vnd_budget_rounds_down_to_whole_shares_and_pnl_stays_native(client, db_session):
    account_id = vnd_signup(client)['accounts'][0]['id']
    quote(db_session)
    reviewed = preview(client, account_id, notional=1000000)
    data = reviewed.json()
    assert data['currency'] == 'VND' and Decimal(data['quantity']) == 19
    assert Decimal(data['estimated_total']) == 988000
    assert Decimal(data['cash_after']) == 999012000
    order = confirm(client, reviewed)
    assert order['currency'] == 'VND'
    assert Decimal(order['execution']['cash_after']) == 999012000
    assert client.post('/orders/confirm', json={'preview_id': data['id']}).json()['id'] == order['id']
    quote(db_session, 55000, when=datetime.utcnow()+timedelta(seconds=1))
    confirm(client, preview(client, account_id, side='SELL', quantity=4))
    overview = client.get(f'/accounts/{account_id}/overview').json()
    assert overview['summary']['currency'] == 'VND'
    assert Decimal(overview['summary']['realized_pnl']) == 12000
    assert Decimal(overview['summary']['unrealized_pnl']) == 45000
    assert Decimal(overview['summary']['total_pnl']) == 57000
    assert Decimal(overview['summary']['equity']) == 1000057000
    assert all(t['currency'] == 'VND' for t in overview['trades'])
    assert overview['positions'][0]['currency'] == 'VND'
    assert overview['quotes'][0]['currency'] == 'VND'


def test_vnd_reprice_preserves_budget(client, db_session):
    account_id = vnd_signup(client)['accounts'][0]['id']
    quote(db_session)
    reviewed = preview(client, account_id, notional=1000000)
    quote(db_session, 60000, when=datetime.utcnow()+timedelta(seconds=1))
    order = confirm(client, reviewed)
    assert Decimal(order['quantity']) == 16
    assert Decimal(order['execution']['cash_after']) == 999040000


@pytest.mark.parametrize('payload', [{'quantity': '1.5'}, {'notional': '1000000.5'},
    {'quantity': 1, 'order_type': 'LIMIT', 'limit_price': '50000.5'}, {'notional': 100}])
def test_vnd_rejects_fractional_units_and_underfunded_share_budget(client, db_session, payload):
    account_id = vnd_signup(client)['accounts'][0]['id']
    quote(db_session)
    assert preview(client, account_id, **payload).status_code == 400
    assert db_session.query(Order).count() == db_session.query(Trade).count() == 0
    assert db_session.get(Account, account_id).cash_balance == 1000000000


def test_currency_mismatch_cannot_preview_place_or_worker_fill(client, db_session):
    account_id = signup(client)['accounts'][0]['id']
    quote(db_session)
    for payload in ({'quantity': 1}, {'quantity': 1, 'order_type': 'LIMIT', 'limit_price': 50000}):
        failed = preview(client, account_id, **payload)
        assert failed.status_code == 400 and 'VND' in failed.json()['detail']
        direct = client.post('/orders/', json={'account_id': account_id, 'symbol': 'VNM.VN', 'side': 'BUY', **payload})
        assert direct.status_code == 400
    legacy = Order(account_id=account_id, symbol='VNM.VN', side=OrderSide.BUY, order_type=OrderType.LIMIT,
        quantity=1, limit_price=60000, status=OrderStatus.PENDING, filled_quantity=0,
        created_at=datetime.utcnow()-timedelta(minutes=1))
    db_session.add(legacy); db_session.commit()
    assert process_pending_limit_orders(db_session, account_id=account_id)['filled'] == 0
    assert db_session.query(Trade).count() == db_session.query(Position).count() == 0
    assert db_session.get(Account, account_id).cash_balance == 100000


def test_vnd_reservation_cancel_and_worker_fill(client, db_session):
    account_id = vnd_signup(client)['accounts'][0]['id']
    quote(db_session)
    order = confirm(client, preview(client, account_id, quantity=100, order_type='LIMIT', limit_price=50000))
    assert order['status'] == 'PENDING'
    summary = client.get(f'/accounts/{account_id}/summary').json()
    assert Decimal(summary['reserved_cash']) == 5000000
    assert Decimal(summary['available_cash']) == 995000000
    assert client.post(f"/orders/{order['id']}/cancel").status_code == 200
    assert Decimal(client.get(f'/accounts/{account_id}/summary').json()['reserved_cash']) == 0
    order = confirm(client, preview(client, account_id, quantity=100, order_type='LIMIT', limit_price=50000))
    quote(db_session, 49000, when=datetime.utcnow()+timedelta(seconds=1))
    assert process_pending_limit_orders(db_session, account_id=account_id)['filled'] == 1
    assert process_pending_limit_orders(db_session, account_id=account_id)['filled'] == 0
    assert db_session.get(Account, account_id).cash_balance == 995100000


def test_unknown_or_changed_quote_currency_blocks_confirmation_and_valuation(client, db_session):
    account_id = vnd_signup(client)['accounts'][0]['id']
    bar = quote(db_session)
    reviewed = preview(client, account_id, quantity=2)
    bar.currency = 'USD'; db_session.commit()
    failed = client.post('/orders/confirm', json={'preview_id': reviewed.json()['id']})
    assert failed.status_code == 400
    assert db_session.query(Trade).count() == 0
    quote(db_session, when=datetime.utcnow()+timedelta(seconds=1))
    confirm(client, preview(client, account_id, quantity=2))
    quote(db_session, currency='USD', when=datetime.utcnow()+timedelta(seconds=2))
    assert client.get(f'/accounts/{account_id}/summary').status_code == 409
    assert client.get(f'/accounts/{account_id}/overview').status_code == 409
    quote(db_session, symbol='UNKNOWN.L', currency=None)
    failed = preview(client, account_id, symbol='UNKNOWN.L', quantity=1)
    assert failed.status_code == 400 and 'currency is unavailable' in failed.json()['detail']


def test_bulk_quotes_preserve_vnd_without_rescaling(client, db_session, monkeypatch):
    from app.api import prices
    monkeypatch.setattr(prices, '_get_live_item', lambda *args, **kwargs: {'timestamp': datetime.utcnow(),
        'open': 52000, 'high': 52000, 'low': 52000, 'close': 52000, 'currency': 'VND', 'exchange': 'VSE'})
    response = client.post('/prices/latest/bulk', json=['VNM.VN'])
    assert response.status_code == 200, response.text
    assert response.json()[0]['currency'] == 'VND' and Decimal(str(response.json()[0]['close'])) == 52000
    assert client.get('/prices/latest?symbol=VNM.VN').json()['currency'] == 'VND'


def test_currency_migration_preserves_legacy_balances_and_does_not_guess_foreign_currency(db_session, account_with_price):
    engine = db_session.get_bind()
    db_session.add(Symbol(symbol='AAPL', name='Apple'))
    db_session.add(Symbol(symbol='UNKNOWN.L', name='Unknown'))
    db_session.commit(); db_session.expire_all()
    with engine.begin() as connection:
        for table, columns in {'accounts': ['currency'], 'symbols': ['currency', 'exchange'], 'price_bars': ['currency']}.items():
            for column in columns:
                connection.execute(text(f'ALTER TABLE {table} DROP COLUMN {column}'))
        assert missing_currency_columns(connection)
    migrate_currencies(engine); migrate_currencies(engine)
    with engine.connect() as connection:
        assert not missing_currency_columns(connection)
        assert connection.execute(text('SELECT currency, cash_balance FROM accounts')).one() == ('USD', Decimal(10000))
        assert connection.execute(text("SELECT currency FROM symbols WHERE symbol='AAPL'")).scalar() == 'USD'
        assert connection.execute(text("SELECT currency FROM symbols WHERE symbol='UNKNOWN.L'")).scalar() is None
        assert connection.execute(text('SELECT close FROM price_bars')).scalar() == 100


def test_vietnam_search_distinguishes_us_etf_and_validates_hose_listing(client, db_session, monkeypatch):
    # Legacy cached names must not hide provider currency/exchange enrichment.
    db_session.add_all([Symbol(symbol='VNM', name='Vietnam ETF'), Symbol(symbol='VNM.VN', name='Vinamilk')])
    db_session.commit()
    quotes = [{'symbol': 'VNM', 'shortname': 'VanEck Vietnam ETF', 'quoteType': 'ETF', 'exchange': 'BTS', 'exchDisp': 'BATS Trading'}]
    monkeypatch.setattr(symbol_search.yf, 'Search', lambda *args, **kwargs: SimpleNamespace(response={'quotes': quotes}, quotes=quotes))
    monkeypatch.setattr(symbol_search.yf, 'Ticker', lambda *args: SimpleNamespace(
        history=lambda **kwargs: SimpleNamespace(empty=False),
        get_history_metadata=lambda: {'currency': 'VND', 'exchangeName': 'VSE', 'longName': 'Vinamilk'}))
    result = client.get('/symbols/search?q=VNM').json()
    assert {(item['symbol'], item['currency']) for item in result} == {('VNM', 'USD'), ('VNM.VN', 'VND')}
    assert client.get('/symbols/search?q=Vinamilk').json()[-1]['symbol'] == 'VNM.VN'
    assert any(item['symbol'] == 'VNM.VN' for item in client.get('/symbols/search?q=VNM.VN').json())
