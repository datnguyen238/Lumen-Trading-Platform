from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.orders import OrderCreate, OrderRead
from app.services.execution import execute_market_order

router = APIRouter()


@router.post("/market", response_model=OrderRead)
def market(order_in: OrderCreate, db: Session = Depends(get_db)):
    try:
        return execute_market_order(db, order_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
