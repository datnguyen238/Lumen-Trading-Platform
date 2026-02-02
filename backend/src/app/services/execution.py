from decimal import Decimal
from sqlalchemy.orm import Session

from app.models.models import Account, Order, Trade
from app.models.enums import OrderStatus, OrderType
from app.schemas.orders import OrderCreate
from app.services.pricing import get_last_close
from app.services.positions import apply_fill


def execute_market_order(db: Session, order_in: OrderCreate) -> Order:
    account = db.query(Account).filter(Account.id == order_in.account_id).first()
    if not account:
        raise ValueError("Account not found")

    if order_in.order_type != OrderType.MARKET:
        raise ValueError("Only MARKET orders supported in v1")

    price = get_last_close(db, order_in.symbol)
    qty = Decimal(order_in.quantity)

    cost = qty * price
    if order_in.side.value == "BUY" and Decimal(account.cash_balance) < cost:
        raise ValueError("Insufficient cash balance")

    order = Order(
        account_id=account.id,
        symbol=order_in.symbol,
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
    db.refresh(order)

    trade = Trade(
        account_id=account.id,
        order_id=order.id,
        symbol=order.symbol,
        side=order.side,
        quantity=qty,
        price=price,
    )
    db.add(trade)

    apply_fill(db, account, order.symbol, order.side, qty, price)

    db.commit()
    db.refresh(order)
    return order
