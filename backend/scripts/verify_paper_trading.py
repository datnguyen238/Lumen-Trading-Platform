"""Run a real-database API round trip inside an outer transaction, then roll it back.

Run from backend: .venv/bin/python scripts/verify_paper_trading.py
Start the API once first so its additive tables and privacy settings exist.
No account, order, watchlist entry, credential, session or quote from this check is committed.
"""
import sys
import uuid
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.main import app
from app.db.session import engine, get_db
from app.models.models import PriceBar, User
from app.api import orders
from app.services.pricing import get_execution_quote

email = f'backend-check-{uuid.uuid4().hex}@example.com'
checks = []
connection = engine.connect()
transaction = connection.begin()
db = Session(bind=connection, join_transaction_mode='create_savepoint', autoflush=False)
original_refresh = orders.refresh_execution_quote


def result(response, code=200):
    if response.status_code != code:
        raise AssertionError(f'Unexpected API response ({response.status_code}): {response.text}')
    return response.json()


def override():
    yield db


try:
    app.dependency_overrides[get_db] = override
    orders.refresh_execution_quote = get_execution_quote
    db.add(PriceBar(symbol='LUMENTEST', timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
                    open=10, high=10, low=10, close=10, volume=1000))
    db.commit()
    # Deliberately omit TestClient's lifespan: worker/schema startup belongs to the running API.
    client = TestClient(app)
    data = result(client.post('/auth/signup', json={'email': email, 'full_name': 'Backend verification', 'password': uuid.uuid4().hex}))
    client.headers['X-CSRF-Token'] = data['csrf_token']
    account_id = data['accounts'][0]['id']
    assert Decimal(data['accounts'][0]['cash_balance']) == 100000
    checks.append('signup and private persistent session')
    result(client.get('/auth/me'))
    body = {'account_id': account_id, 'symbol': 'LUMENTEST', 'side': 'BUY', 'notional': 250}
    preview = result(client.post('/orders/preview', json=body))
    order = result(client.post('/orders/confirm', json={'preview_id': preview['id']}))
    assert Decimal(order['filled_quantity']) == 25
    assert result(client.post('/orders/confirm', json={'preview_id': preview['id']}))['id'] == order['id']
    checks.append('server-reviewed dollar buy and duplicate-confirm protection')
    preview = result(client.post('/orders/preview', json={'account_id': account_id, 'symbol': 'LUMENTEST', 'side': 'SELL', 'quantity': 5}))
    result(client.post('/orders/confirm', json={'preview_id': preview['id']}))
    overview = result(client.get(f'/accounts/{account_id}/overview'))
    assert Decimal(overview['summary']['equity']) == 100000
    assert Decimal(overview['summary']['positions']['LUMENTEST']['quantity']) == 20
    assert len(overview['trades']) == 2
    checks.append('sell, cash accounting, holdings, and execution receipts')
    preview = result(client.post('/orders/preview', json={'account_id': account_id, 'symbol': 'LUMENTEST', 'side': 'BUY', 'quantity': 1, 'order_type': 'LIMIT', 'limit_price': 1}))
    limit = result(client.post('/orders/confirm', json={'preview_id': preview['id']}))
    assert limit['status'] == 'PENDING'
    assert Decimal(result(client.get(f'/accounts/{account_id}/summary'))['reserved_cash']) == 1
    result(client.post(f"/orders/{limit['id']}/cancel"))
    checks.append('limit reservation and cancellation')
    assert result(client.put('/watchlist/LUMENTEST')) == ['LUMENTEST']
    assert result(client.get('/watchlist')) == ['LUMENTEST']
    checks.append('database-backed watchlist')
    result(client.post('/auth/logout', json={}))
    result(client.get('/auth/me'), 401)
    checks.append('logout revokes server session')
finally:
    app.dependency_overrides.clear()
    orders.refresh_execution_quote = original_refresh
    db.close()
    transaction.rollback()
    connection.close()

with engine.connect() as connection:
    assert connection.execute(select(User.id).where(User.email == email)).first() is None
for check in checks:
    print('PASS', check)
print('PASS outer transaction rolled back; no verification account or trade retained')
