from decimal import Decimal

import pytest

from app.models.enums import OrderSide, OrderType
from app.models.models import Position, Trade
from app.schemas.orders import OrderCreate
from app.services.execution import execute_market_order


def test_rejects_non_positive_quantity(db_session, account_with_price):
    order_in = OrderCreate(
        account_id=account_with_price.id,
        symbol="AAPL",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=Decimal("0"),
    )

    with pytest.raises(ValueError, match="Quantity must be greater than 0"):
        execute_market_order(db_session, order_in)


def test_rejects_buy_when_insufficient_cash(db_session, account_with_price):
    order_in = OrderCreate(
        account_id=account_with_price.id,
        symbol="AAPL",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=Decimal("1000"),
    )

    with pytest.raises(ValueError, match="Insufficient cash balance"):
        execute_market_order(db_session, order_in)


def test_rejects_sell_when_insufficient_position(db_session, account_with_price):
    order_in = OrderCreate(
        account_id=account_with_price.id,
        symbol="AAPL",
        side=OrderSide.SELL,
        order_type=OrderType.MARKET,
        quantity=Decimal("1"),
    )

    with pytest.raises(ValueError, match="Insufficient position quantity"):
        execute_market_order(db_session, order_in)


def test_successful_buy_writes_order_trade_and_updates_account(db_session, account_with_price):
    order_in = OrderCreate(
        account_id=account_with_price.id,
        symbol="aapl",  # verify normalization to uppercase
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=Decimal("2"),
    )

    order = execute_market_order(db_session, order_in)

    assert order.symbol == "AAPL"
    assert order.filled_quantity == Decimal("2")
    assert order.avg_fill_price == Decimal("100")

    trade = db_session.query(Trade).filter(Trade.order_id == order.id).first()
    assert trade is not None
    assert trade.symbol == "AAPL"
    assert trade.quantity == Decimal("2")
    assert trade.price == Decimal("100")

    position = (
        db_session.query(Position)
        .filter(Position.account_id == account_with_price.id, Position.symbol == "AAPL")
        .first()
    )
    assert position is not None
    assert position.quantity == Decimal("2")
    assert position.average_price == Decimal("100")

    db_session.refresh(account_with_price)
    assert Decimal(account_with_price.cash_balance) == Decimal("9800")


def test_successful_sell_writes_order_trade_and_updates_account(db_session, account_with_price):
    db_session.add(
        Position(
            account_id=account_with_price.id,
            symbol="AAPL",
            quantity=Decimal("3"),
            average_price=Decimal("95"),
        )
    )
    db_session.commit()

    order_in = OrderCreate(
        account_id=account_with_price.id,
        symbol="AAPL",
        side=OrderSide.SELL,
        order_type=OrderType.MARKET,
        quantity=Decimal("1"),
    )

    order = execute_market_order(db_session, order_in)

    assert order.symbol == "AAPL"
    assert order.filled_quantity == Decimal("1")
    assert order.avg_fill_price == Decimal("100")

    trade = db_session.query(Trade).filter(Trade.order_id == order.id).first()
    assert trade is not None
    assert trade.side == OrderSide.SELL
    assert trade.quantity == Decimal("1")
    assert trade.price == Decimal("100")

    position = (
        db_session.query(Position)
        .filter(Position.account_id == account_with_price.id, Position.symbol == "AAPL")
        .first()
    )
    assert position is not None
    assert position.quantity == Decimal("2")

    db_session.refresh(account_with_price)
    assert Decimal(account_with_price.cash_balance) == Decimal("10100")
