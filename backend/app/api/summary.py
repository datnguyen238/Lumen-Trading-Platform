from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from decimal import Decimal

from app.db.session import get_db
from app.models.models import Account, Position, Trade
from app.models.enums import OrderSide
from app.schemas.summary import AccountSummary, SymbolPnL
from app.services.pricing import get_mark_price

router = APIRouter()


def _compute_realized_pnl(db: Session, account_id: int) -> Decimal:
    trades = (
        db.query(Trade)
        .filter(Trade.account_id == account_id)
        .order_by(Trade.executed_at.asc(), Trade.id.asc())
        .all()
    )

    state: dict[str, dict[str, Decimal]] = {}
    realized_total = Decimal("0")

    for t in trades:
        symbol = str(t.symbol).strip().upper()
        qty = Decimal(t.quantity)
        price = Decimal(t.price)
        s = state.setdefault(symbol, {"qty": Decimal("0"), "avg": Decimal("0")})

        if t.side == OrderSide.BUY:
            new_qty = s["qty"] + qty
            if new_qty > 0:
                s["avg"] = ((s["avg"] * s["qty"]) + (price * qty)) / new_qty
            s["qty"] = new_qty
        else:
            sell_qty = min(qty, s["qty"])
            realized_total += (price - s["avg"]) * sell_qty
            s["qty"] = s["qty"] - sell_qty
            if s["qty"] == 0:
                s["avg"] = Decimal("0")

    return realized_total


@router.get("/accounts/{account_id}/summary", response_model=AccountSummary)
def account_summary(account_id: int, db: Session = Depends(get_db)):
    acc = db.query(Account).filter(Account.id == account_id).first()
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")

    positions = db.query(Position).filter(Position.account_id == account_id).all()

    cash = Decimal(acc.cash_balance)
    realized_total = _compute_realized_pnl(db, account_id)
    unrealized_total = Decimal("0")
    market_value_total = Decimal("0")
    out_positions = {}

    for p in positions:
        qty = Decimal(p.quantity)
        if qty == 0:
            continue

        avg_cost = Decimal(p.average_price)
        mark = get_mark_price(db, p.symbol)
        market_value = mark * qty
        unrealized = (mark - avg_cost) * qty
        market_value_total += market_value
        unrealized_total += unrealized

        out_positions[p.symbol] = SymbolPnL(
            symbol=p.symbol,
            quantity=qty,
            avg_cost=avg_cost,
            mark_price=mark,
            market_value=market_value,
            unrealized_pnl=unrealized,
        )

    # Net liquidation value: cash + current marked value of open positions
    equity = cash + market_value_total

    return AccountSummary(
        account_id=account_id,
        cash=cash,
        equity=equity,
        market_value=market_value_total,
        realized_pnl=realized_total,
        unrealized_pnl=unrealized_total,
        total_pnl=realized_total + unrealized_total,
        positions=out_positions,
    )
