import os
os.environ["PAPER_WORKER_ENABLED"] = "false"
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.models import Account, PriceBar, User


@pytest.fixture()
def db_session():
    postgres_url = os.getenv("TEST_POSTGRES_URL")
    schema = None
    admin_engine = None
    if postgres_url:
        # Dedicated local test cluster only; never accept the project's Supabase URL.
        if "/tmp/lumen-paper-postgres" not in postgres_url or "lumen_test" not in postgres_url:
            raise RuntimeError("TEST_POSTGRES_URL must target the isolated local test cluster")
        import uuid
        from sqlalchemy import text
        schema = "test_" + uuid.uuid4().hex
        admin_engine = create_engine(postgres_url)
        with admin_engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        engine = create_engine(postgres_url, connect_args={"options": f"-csearch_path={schema}"})
    else:
        engine = create_engine("sqlite+pysqlite:///:memory:", future=True,
            poolclass=StaticPool, connect_args={"check_same_thread": False})
    if engine.dialect.name == "sqlite":
        from sqlalchemy import event
        @event.listens_for(engine, "connect")
        def foreign_keys(connection, record):
            connection.execute("PRAGMA foreign_keys=ON")
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
        if admin_engine:
            from sqlalchemy import text
            with admin_engine.begin() as connection:
                connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
            admin_engine.dispose()


@pytest.fixture()
def account_with_price(db_session):
    user = User(email="trader@example.com", full_name="Trader")
    db_session.add(user)
    db_session.flush()

    account = Account(user_id=user.id, name="Main", cash_balance=10000)
    db_session.add(account)
    db_session.flush()

    bar = PriceBar(
        symbol="AAPL",
        timestamp=datetime.utcnow() - timedelta(days=1),
        open=100,
        high=110,
        low=90,
        close=100,
        volume=1000000,
    )
    db_session.add(bar)
    db_session.commit()
    db_session.refresh(account)
    return account


@pytest.fixture()
def client(db_session, monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.db.session import get_db
    from app.api.auth import _attempts
    _attempts.clear()
    # Tests exercise execution using seeded observations, with no market-data network calls.
    from app.api import orders
    from app.services.pricing import get_execution_quote
    # FX tests seed observed rates explicitly; an absent rate is an offline outage.
    from app.services import fx
    def unavailable_fx():
        raise ValueError("Offline test: no FX provider observation")
    monkeypatch.setattr(fx, "_fetch_usd_vnd", unavailable_fx)
    original_refresh = orders.refresh_execution_quote
    orders.refresh_execution_quote = get_execution_quote
    def override():
        yield db_session
    app.dependency_overrides[get_db] = override
    with TestClient(app) as client:
        yield client
    orders.refresh_execution_quote = original_refresh
    app.dependency_overrides.clear()
