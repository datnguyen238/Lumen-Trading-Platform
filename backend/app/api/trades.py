from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.db.session import get_db
from app.models.models import Account, Trade
from app.schemas.trades import TradeRead

router = APIRouter()


@router.get("/accounts/{account_id}/trades", response_model=list[TradeRead])
def get_trades(account_id: int, db: Session = Depends(get_db)):
    acc = db.query(Account).filter(Account.id == account_id).first()
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")

    rows = (
        db.query(Trade)
        .filter(Trade.account_id == account_id)
        .order_by(desc(Trade.executed_at))
        .all()
    )
    return rows
