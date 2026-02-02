from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from decimal import Decimal

from app.db.session import get_db
from app.models.models import Account, Position
from app.schemas.summary import AccountSummary, SymbolPnL
from app.services.pricing import get_mark_price

router = APIRouter()


@router.get("/accounts/{account_id}/summary", response_model=AccountSummary)
def account_summary(account_id: int, db: Session = Depends(get_db)):
    acc = db.query(Account).filter(Account.id == account_id).first()
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")

    positions = db.query(Position).filter(Position.account_id == account_id).all()

    cash = Decimal(acc.cash_balance)
    unrealized_total = Decimal("0")
    out_positions = {}

    for p in positions:
        qty = Decimal(p.quantity)
        if qty == 0:
            continue

        avg_cost = Decimal(p.average_price)
        mark = get_mark_price(db, p.symbol)
        unrealized = (mark - avg_cost) * qty
        unrealized_total += unrealized

        out_positions[p.symbol] = SymbolPnL(
            symbol=p.symbol,
            quantity=qty,
            avg_cost=avg_cost,
            mark_price=mark,
            unrealized_pnl=unrealized,
        )

    equity = cash + unrealized_total

    return AccountSummary(
        account_id=account_id,
        cash=cash,
        equity=equity,
        unrealized_pnl=unrealized_total,
        positions=out_positions,
    )
