from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.db.session import get_db
from app.models.models import Account, Order
from app.schemas.orders import OrderRead

router = APIRouter()


@router.get("/accounts/{account_id}/orders", response_model=list[OrderRead])
def get_orders(account_id: int, db: Session = Depends(get_db)):
    acc = db.query(Account).filter(Account.id == account_id).first()
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")

    rows = (
        db.query(Order)
        .filter(Order.account_id == account_id)
        .order_by(desc(Order.created_at))
        .all()
    )
    return rows
