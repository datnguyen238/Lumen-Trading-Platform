from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.orders import OrderCreate, OrderRead
from app.services.execution import (
    execute_market_order,
    place_order,
    cancel_order,
    process_pending_limit_orders,
)

router = APIRouter()


@router.post("/market", response_model=OrderRead)
def market(order_in: OrderCreate, db: Session = Depends(get_db)):
    try:
        return execute_market_order(db, order_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/", response_model=OrderRead)
def create_order(order_in: OrderCreate, db: Session = Depends(get_db)):
    try:
        return place_order(db, order_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{order_id}/cancel", response_model=OrderRead)
def cancel(order_id: int, account_id: int | None = None, db: Session = Depends(get_db)):
    try:
        return cancel_order(db, order_id=order_id, account_id=account_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/process-pending")
def process_pending(symbol: str | None = None, limit: int = 100, db: Session = Depends(get_db)):
    return process_pending_limit_orders(db, symbol=symbol, limit=limit)
