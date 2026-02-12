from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.models import Account, PriceBar, User


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


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
        timestamp=datetime(2026, 2, 7, 0, 0, 0),
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
