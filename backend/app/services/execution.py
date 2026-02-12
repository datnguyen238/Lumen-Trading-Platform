from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.models import Account, Order, Trade, Position
from app.models.enums import OrderStatus, OrderType
from app.schemas.orders import OrderCreate
from app.services.pricing import get_last_close
from app.services.positions import apply_fill


def execute_market_order(db: Session, order_in: OrderCreate) -> Order:
    symbol = str(order_in.symbol).strip().upper()
    if not symbol:
        raise ValueError("Symbol is required")

    qty = Decimal(order_in.quantity)
    if qty <= 0:
        raise ValueError("Quantity must be greater than 0")

    if order_in.order_type != OrderType.MARKET:
        raise ValueError("Only MARKET orders supported in v1")

    account = db.query(Account).filter(Account.id == order_in.account_id).first()
    if not account:
        raise ValueError("Account not found")

    price = get_last_close(db, symbol)
    cost = qty * price

    if order_in.side.value == "BUY" and Decimal(account.cash_balance) < cost:
        raise ValueError("Insufficient cash balance")

    if order_in.side.value == "SELL":
        pos = (
            db.query(Position)
            .filter(and_(Position.account_id == account.id, Position.symbol == symbol))
            .first()
        )
        if not pos or Decimal(pos.quantity) < qty:
            raise ValueError("Insufficient position quantity")

    try:
        order = Order(
            account_id=account.id,
            symbol=symbol,
            side=order_in.side,
            order_type=order_in.order_type,
            quantity=qty,
            limit_price=order_in.limit_price,
            status=OrderStatus.FILLED,
            filled_quantity=qty,
            avg_fill_price=price,
        )
        db.add(order)
        db.flush()

        trade = Trade(
            account_id=account.id,
            order_id=order.id,
            symbol=symbol,
            side=order_in.side,
            quantity=qty,
            price=price,
        )
        db.add(trade)

        apply_fill(db, account, symbol, order_in.side, qty, price)
        db.commit()
        db.refresh(order)
        return order
    except Exception:
        db.rollback()
        raise
