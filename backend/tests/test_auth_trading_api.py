from datetime import datetime, timedelta
from decimal import Decimal
import pytest
from app.models.models import Account, AuthSession, Order, Position, PriceBar, Trade, User, UserCredential
from app.models.enums import OrderSide, OrderStatus, OrderType
from app.schemas.orders import OrderCreate
from app.services.execution import execute_market_order, place_order, process_pending_limit_orders


def signup(client, email="beginner@example.com"):
    response = client.post("/auth/signup", json={"email": email, "full_name": "Beginner", "password": "practice123"})
    assert response.status_code == 200, response.text
    data = response.json()
    client.headers["X-CSRF-Token"] = data["csrf_token"]
    return data


def test_signup_login_logout_and_private_ownership(client, db_session):
    assert client.get("/accounts/1").status_code == 401
    response = client.post("/auth/signup", json={"email": "beginner@example.com", "full_name": "Beginner", "password": "practice123"})
    assert response.status_code == 200
    assert "HttpOnly" in response.headers["set-cookie"] and "SameSite=lax" in response.headers["set-cookie"]
    data = response.json(); client.headers["X-CSRF-Token"] = data["csrf_token"]
    account_id = data["accounts"][0]["id"]
    assert Decimal(data["accounts"][0]["cash_balance"]) == 100000
    assert "practice123" not in db_session.get(UserCredential, data["user"]["id"]).password_hash
    assert client.get("/auth/me").json()["user"]["id"] == data["user"]["id"]
    token = client.cookies.get("lumen_session")
    assert client.post("/auth/logout", json={}).status_code == 200
    assert client.get(f"/accounts/{account_id}").status_code == 401
    assert client.post("/auth/login", json={"email": "beginner@example.com", "password": "wrong"}).status_code == 401
    login = client.post("/auth/login", json={"email": "BEGINNER@example.com", "password": "practice123"})
    assert login.status_code == 200
    assert client.cookies.get("lumen_session") != token
    client.headers["X-CSRF-Token"] = login.json()["csrf_token"]
    assert client.get(f"/accounts/{account_id}").status_code == 200
    other = User(email="other@example.com"); db_session.add(other); db_session.flush()
    foreign = Account(user_id=other.id, name="Private", cash_balance=500)
    db_session.add(foreign); db_session.commit()
    for suffix in ("", "/positions", "/orders", "/trades", "/summary"):
        assert client.get(f"/accounts/{foreign.id}{suffix}").status_code == 404
    assert client.get(f"/users/{other.id}").status_code == 404
    assert client.post("/accounts/", json={"user_id": other.id, "name": "Intrusion"}).status_code == 403
    assert client.post("/orders/", json={"account_id": foreign.id, "symbol": "AAPL", "side": "BUY", "quantity": 1}).status_code == 404
    assert client.post(f"/orders/process-pending?account_id={foreign.id}").status_code == 404
    assert client.post("/admin/reset-db?confirm=true").status_code == 404
    assert client.post("/users/", json={"email": "anonymous@example.com"}).status_code in (404,405)


def test_csrf_origin_expiry_and_legacy_account_protection(client, db_session):
    data = signup(client)
    del client.headers["X-CSRF-Token"]
    assert client.post("/accounts/", json={"user_id": data["user"]["id"]}).status_code == 403
    assert client.post("/auth/signup", headers={"Origin": "https://attacker.example"}, json={"email": "intruder@example.com", "full_name": "Intruder", "password": "practice123"}).status_code == 403
    client.headers["X-CSRF-Token"] = data["csrf_token"]
    session = db_session.query(AuthSession).one(); session.expires_at = datetime.utcnow() - timedelta(seconds=1)
    db_session.commit()
    assert client.get("/auth/me").status_code == 401
    db_session.add(User(email="legacy@example.com")); db_session.commit()
    assert client.post("/auth/signup", json={"email": "legacy@example.com", "full_name": "Claimant", "password": "practice123"}).status_code == 409
    assert client.post("/auth/login", json={"email": "legacy@example.com", "password": "practice123"}).status_code == 401


def test_real_api_buy_retry_sell_limit_and_cancel(client, db_session):
    data = signup(client); account_id = data["accounts"][0]["id"]
    db_session.add(PriceBar(symbol="AAPL", timestamp=datetime.utcnow(), open=100, high=100, low=100, close=100)); db_session.commit()
    body = {"account_id": account_id, "symbol": "AAPL", "side": "BUY", "quantity": "2.5", "client_order_id": "first-order-key-1234"}
    buy = client.post("/orders/", json=body)
    assert buy.status_code == 200, buy.text
    assert buy.json()["status"] == "FILLED"
    assert client.post("/orders/", json=body).json()["id"] == buy.json()["id"]
    assert db_session.query(Trade).count() == 1
    assert client.post("/orders/", json={**body, "quantity": 3}).status_code == 400
    summary = client.get(f"/accounts/{account_id}/summary").json()
    assert Decimal(summary["cash"]) == Decimal("99750")
    assert Decimal(summary["positions"]["AAPL"]["quantity"]) == Decimal("2.5")
    assert client.post("/orders/", json={**body, "side": "SELL", "quantity": "1.5", "client_order_id": "sell-order-key-1234"}).status_code == 200
    assert client.post("/orders/", json={**body, "side": "SELL", "quantity": 2, "client_order_id": "sell-too-many-1234"}).status_code == 400
    limit = client.post("/orders/", json={**body, "order_type": "LIMIT", "limit_price": 90, "quantity": 1, "client_order_id": "limit-order-key-1234"})
    assert limit.status_code == 200 and limit.json()["status"] == "PENDING"
    assert client.post(f"/orders/{limit.json()['id']}/cancel").json()["status"] == "CANCELED"
    assert client.post(f"/orders/{limit.json()['id']}/cancel").status_code == 400
    assert Decimal(client.get(f"/accounts/{account_id}/summary").json()["equity"]) == 100000
    for value in ("NaN", "Infinity", "0", "-1", "0.00001"):
        assert client.post("/orders/", json={**body, "quantity": value}).status_code == 422


def test_limit_reservations_matching_and_rollback(db_session, account_with_price):
    account = account_with_price
    pending = place_order(db_session, OrderCreate(account_id=account.id, symbol="AAPL", side=OrderSide.BUY, quantity=100, order_type=OrderType.LIMIT, limit_price=90))
    assert pending.status == OrderStatus.PENDING
    with pytest.raises(ValueError, match="Insufficient cash"):
        execute_market_order(db_session, OrderCreate(account_id=account.id, symbol="AAPL", side=OrderSide.BUY, quantity=11))
    legacy = Order(account_id=account.id, symbol="AAPL", side=OrderSide.BUY, order_type=OrderType.LIMIT, quantity=1000, limit_price=99, status=OrderStatus.PENDING, filled_quantity=0)
    db_session.add(legacy)
    db_session.add(PriceBar(symbol="AAPL", timestamp=datetime.utcnow() + timedelta(seconds=1), open=80, high=80, low=80, close=80)); db_session.commit()
    assert process_pending_limit_orders(db_session, account_id=account.id)["filled"] == 0
    db_session.refresh(account)
    assert account.cash_balance == 10000
    assert db_session.query(Trade).count() == 0
    assert db_session.query(Position).count() == 0
    legacy.status = OrderStatus.CANCELED; db_session.commit()
    assert process_pending_limit_orders(db_session, account_id=account.id)["filled"] == 1
    assert process_pending_limit_orders(db_session, account_id=account.id)["filled"] == 0
    db_session.refresh(account)
    assert account.cash_balance == 2000
    assert db_session.query(Trade).count() == 1
