from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.models import Position, Account
from app.models.enums import OrderSide


def get_or_create_position(db: Session, account_id: int, symbol: str) -> Position:
    pos = (
        db.query(Position)
        .filter(and_(Position.account_id == account_id, Position.symbol == symbol))
        .first()
    )
    if not pos:
        pos = Position(account_id=account_id, symbol=symbol, quantity=Decimal("0"), average_price=Decimal("0"))
        db.add(pos)
        db.flush()
        db.refresh(pos)
    return pos


def apply_fill(db: Session, account: Account, symbol: str, side: OrderSide, qty: Decimal, price: Decimal) -> None:
    pos = get_or_create_position(db, account.id, symbol)

    if side == OrderSide.BUY:
        new_qty = Decimal(pos.quantity) + qty
        if new_qty > 0:
            pos.average_price = (
                (Decimal(pos.average_price) * Decimal(pos.quantity)) + (price * qty)
            ) / new_qty
        pos.quantity = new_qty
        account.cash_balance = Decimal(account.cash_balance) - (qty * price)
    else:
        pos.quantity = Decimal(pos.quantity) - qty
        account.cash_balance = Decimal(account.cash_balance) + (qty * price)

    db.flush()
