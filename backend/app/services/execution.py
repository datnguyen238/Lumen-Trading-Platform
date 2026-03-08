from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.models import Account, Order, Trade, Position
from app.models.enums import OrderStatus, OrderType
from app.schemas.orders import OrderCreate
from app.services.pricing import get_last_close
from app.services.positions import apply_fill


def _validate_order_input(order_in: OrderCreate) -> tuple[str, Decimal]:
    symbol = str(order_in.symbol).strip().upper()
    if not symbol:
        raise ValueError("Symbol is required")

    qty = Decimal(order_in.quantity)
    if qty <= 0:
        raise ValueError("Quantity must be greater than 0")

    return symbol, qty


def execute_market_order(db: Session, order_in: OrderCreate) -> Order:
    symbol, qty = _validate_order_input(order_in)

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


def place_order(db: Session, order_in: OrderCreate) -> Order:
    symbol, qty = _validate_order_input(order_in)

    account = db.query(Account).filter(Account.id == order_in.account_id).first()
    if not account:
        raise ValueError("Account not found")

    if order_in.order_type == OrderType.MARKET:
        return execute_market_order(db, order_in)

    if order_in.order_type != OrderType.LIMIT:
        raise ValueError("Unsupported order_type")

    if order_in.limit_price is None or Decimal(order_in.limit_price) <= 0:
        raise ValueError("Valid limit_price is required for LIMIT orders")

    # v1 does not reserve buying power; checks happen again at fill time.
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
            limit_price=Decimal(order_in.limit_price),
            status=OrderStatus.PENDING,
            filled_quantity=Decimal("0"),
            avg_fill_price=None,
        )
        db.add(order)
        db.commit()
        db.refresh(order)
        return order
    except Exception:
        db.rollback()
        raise


def cancel_order(db: Session, order_id: int, account_id: int | None = None) -> Order:
    q = db.query(Order).filter(Order.id == order_id)
    if account_id is not None:
        q = q.filter(Order.account_id == account_id)
    order = q.first()
    if not order:
        raise ValueError("Order not found")
    if order.status in (OrderStatus.FILLED, OrderStatus.CANCELED):
        raise ValueError("Order is already closed")

    order.status = OrderStatus.CANCELED
    db.commit()
    db.refresh(order)
    return order


def process_pending_limit_orders(db: Session, symbol: str | None = None, limit: int = 100) -> dict:
    q = (
        db.query(Order)
        .filter(Order.order_type == OrderType.LIMIT, Order.status == OrderStatus.PENDING)
        .order_by(Order.created_at.asc())
    )
    if symbol:
        q = q.filter(Order.symbol == symbol.strip().upper())

    orders = q.limit(max(1, limit)).all()
    filled = 0
    skipped = 0

    for order in orders:
        try:
            mark = get_last_close(db, order.symbol)
            limit_px = Decimal(order.limit_price) if order.limit_price is not None else None
            if limit_px is None:
                skipped += 1
                continue

            can_fill = (
                (order.side.value == "BUY" and mark <= limit_px)
                or (order.side.value == "SELL" and mark >= limit_px)
            )
            if not can_fill:
                skipped += 1
                continue

            account = db.query(Account).filter(Account.id == order.account_id).first()
            if not account:
                skipped += 1
                continue

            qty = Decimal(order.quantity) - Decimal(order.filled_quantity)
            if qty <= 0:
                skipped += 1
                continue

            apply_fill(db, account, order.symbol, order.side, qty, mark)
            trade = Trade(
                account_id=order.account_id,
                order_id=order.id,
                symbol=order.symbol,
                side=order.side,
                quantity=qty,
                price=mark,
            )
            db.add(trade)

            order.filled_quantity = Decimal(order.filled_quantity) + qty
            order.avg_fill_price = mark
            order.status = OrderStatus.FILLED
            filled += 1
        except Exception:
            skipped += 1

    db.commit()
    return {"processed": len(orders), "filled": filled, "skipped": skipped}
