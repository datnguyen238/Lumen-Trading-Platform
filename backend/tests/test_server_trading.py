from datetime import datetime, timedelta
from decimal import Decimal
from contextlib import contextmanager
from sqlalchemy import select
from app.models.models import Account, Order, OrderPreview, Position, PriceBar, Trade, ExecutionDetail, SavedAsset
from app.models.enums import OrderSide, OrderType, OrderStatus
from app.schemas.orders import OrderCreate
from app.services.execution import place_order, process_pending_limit_orders
from app.services.order_preview import confirm_preview
from app.services.paper_worker import PaperWorker
from app.services.price_refresh import _upsert_bar
from test_auth_trading_api import signup


def bar(db, value, when=None):
    row = PriceBar(symbol='AAPL', timestamp=when or datetime.utcnow(), open=value, high=value, low=value, close=value)
    db.add(row); db.commit()
    return row


def review(client, account_id, **kwargs):
    return client.post('/orders/preview', json={'account_id': account_id, 'symbol': 'AAPL', 'side': 'BUY', **kwargs})


def test_server_dollar_preview_confirmation_and_receipt(client, db_session):
    account_id = signup(client)['accounts'][0]['id']
    bar(db_session, 100)
    result = review(client, account_id, notional='250')
    assert result.status_code == 200, result.text
    preview = result.json()
    assert Decimal(preview['quantity']) == Decimal('2.5')
    assert Decimal(preview['cash_after']) == Decimal('99750')
    assert db_session.query(Trade).count() == 0  # Reviews never trade or reserve funds.
    # Price moves after review: share count changes, chosen dollar budget does not.
    observation = bar(db_session, 120, datetime.utcnow()+timedelta(seconds=1))
    result = client.post('/orders/confirm', json={'preview_id': preview['id']})
    assert result.status_code == 200, result.text
    order = result.json()
    assert Decimal(order['filled_quantity']) == Decimal('2.0833')
    assert Decimal(order['execution']['cash_before']) == Decimal('100000')
    assert Decimal(order['execution']['cash_after']) >= Decimal('99750')
    assert Decimal(order['execution']['quote_price']) == 120
    assert order['execution']['quote_timestamp'] == observation.timestamp.isoformat()
    retry = client.post('/orders/confirm', json={'preview_id': preview['id']})
    assert retry.json()['id'] == order['id']
    assert db_session.query(Trade).count() == 1
    overview = client.get(f'/accounts/{account_id}/overview')
    assert overview.status_code == 200, overview.text
    data = overview.json()
    assert Decimal(data['summary']['equity']) == Decimal('100000')
    assert data['orders'][0]['execution'] is not None


def test_review_expiry_and_ownership(client, db_session):
    account_id = signup(client)['accounts'][0]['id']
    bar(db_session, 100)
    preview = review(client, account_id, quantity='1').json()
    stored = db_session.get(OrderPreview, preview['id'])
    stored.expires_at = datetime.utcnow() - timedelta(seconds=1); db_session.commit()
    expired = client.post('/orders/confirm', json={'preview_id': preview['id']})
    assert expired.status_code == 400 and 'expired' in expired.json()['detail']
    assert db_session.query(Trade).count() == 0
    other = signup(client, 'second@example.com')
    assert client.post('/orders/confirm', json={'preview_id': preview['id']}).status_code == 404
    assert client.get(f'/accounts/{account_id}/overview').status_code == 404
    assert review(client, account_id, quantity='1').status_code == 404


def test_reservations_come_from_server_and_cancel_releases_them(client, db_session):
    account_id = signup(client)['accounts'][0]['id']
    bar(db_session, 100)
    preview = review(client, account_id, quantity='1000', order_type='LIMIT', limit_price='90').json()
    order = client.post('/orders/confirm', json={'preview_id': preview['id']}).json()
    assert order['status'] == 'PENDING'
    summary = client.get(f'/accounts/{account_id}/summary').json()
    assert Decimal(summary['reserved_cash']) == 90000
    assert Decimal(summary['available_cash']) == 10000
    assert review(client, account_id, notional='10001').status_code == 400
    assert client.post(f"/orders/{order['id']}/cancel").status_code == 200
    assert Decimal(client.get(f'/accounts/{account_id}/summary').json()['available_cash']) == 100000


def test_rejects_stale_future_and_invalid_order_inputs(client, db_session):
    account_id = signup(client)['accounts'][0]['id']
    old = bar(db_session, 100, datetime.utcnow()-timedelta(days=8))
    assert review(client, account_id, notional=100).status_code == 400
    future = bar(db_session, 100, datetime.utcnow()+timedelta(days=1))
    assert review(client, account_id, notional=100).status_code == 400
    for payload in ({'quantity': 1, 'notional': 100}, {}, {'notional': 'NaN'}, {'quantity': 'Infinity'},
                    {'notional': 100, 'side': 'SELL'}, {'quantity': 1, 'order_type': 'LIMIT'},
                    {'quantity': 1, 'limit_price': 99}, {'notional': '.99'}):
        assert review(client, account_id, **payload).status_code == 422
    assert db_session.query(Trade).count() == 0


def test_saved_assets_survive_new_session_and_are_private(client, db_session):
    first = signup(client)
    assert client.put('/watchlist/AAPL').json() == ['AAPL']
    assert client.put('/watchlist/AAPL').json() == ['AAPL']
    client.put('/watchlist/MSFT')
    assert db_session.query(SavedAsset).count() == 2
    second = signup(client, 'second@example.com')
    assert client.get('/watchlist').json() == []
    client.put('/watchlist/NVDA')
    response = client.post('/auth/login', json={'email': first['user']['email'], 'password': 'practice123'})
    client.headers['X-CSRF-Token'] = response.json()['csrf_token']
    assert set(client.get('/watchlist').json()) == {'AAPL', 'MSFT'}
    assert client.delete('/watchlist/AAPL').json() == ['MSFT']
    assert client.put('/watchlist/<script>').status_code == 422


def test_worker_fills_without_a_browser_and_ignores_pre_order_quotes(db_session, account_with_price, monkeypatch):
    account = account_with_price
    order = place_order(db_session, OrderCreate(account_id=account.id, symbol='AAPL', side=OrderSide.BUY,
                         order_type=OrderType.LIMIT, quantity=2, limit_price=90))
    # A historical price before the order existed cannot fill a resting order.
    bar(db_session, 80, order.created_at-timedelta(seconds=1))
    assert process_pending_limit_orders(db_session, account_id=account.id)['filled'] == 0
    from app.services import paper_worker
    @contextmanager
    def session():
        yield db_session
    monkeypatch.setattr(paper_worker, 'SessionLocal', session)
    def fresh(db, symbol):
        if symbol == 'AAPL':
            row = _upsert_bar(db, symbol, datetime.utcnow()+timedelta(seconds=1), 80, 80, 80, 80, 1000)
            db.commit()
            return row
    monkeypatch.setattr(paper_worker, 'refresh_execution_quote', fresh)
    worker = PaperWorker(); worker.run_once()
    db_session.refresh(order); db_session.refresh(account)
    assert order.status == OrderStatus.FILLED
    assert account.cash_balance == 9840
    assert db_session.query(Trade).count() == 1
    assert db_session.query(ExecutionDetail).one().quote_price == 80
    worker.run_once()
    assert db_session.query(Trade).count() == 1
    assert worker.status['last_success'] is not None
