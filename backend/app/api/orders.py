from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.models import Order, User, OrderPreview, OrderReceipt
from app.schemas.orders import OrderCreate, OrderRead, PreviewRequest, PreviewRead, ConfirmRequest
from app.services.order_preview import create_preview, confirm_preview
from app.services.pricing import refresh_execution_quote
from app.services.fx import refresh_order_fx
from app.services.auth import current_user, owned_account
from app.services.execution import execute_market_order, place_order, cancel_order, process_pending_limit_orders

router = APIRouter()


def _submit(data, db, user, execute):
    owned_account(data.account_id, db, user)
    try:
        if not data.client_order_id or not db.get(OrderReceipt, (data.account_id, data.client_order_id)):
            refresh_order_fx(db, data.account_id, data.symbol)
        return execute(db, data)
    except ValueError as error:
        raise HTTPException(400, str(error))


@router.post("/preview", response_model=PreviewRead)
def preview(data: PreviewRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    owned_account(data.account_id, db, user)
    try:
        refresh_execution_quote(db, data.symbol.strip().upper())
        refresh_order_fx(db, data.account_id, data.symbol)
        return create_preview(db, data)
    except ValueError as error:
        db.rollback()
        raise HTTPException(400, str(error))


@router.post("/confirm", response_model=OrderRead)
def confirm(data: ConfirmRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    item = db.get(OrderPreview, data.preview_id)
    if not item:
        raise HTTPException(404, "Trade review not found. Review your order again.")
    owned_account(item.account_id, db, user)
    try:
        account_id, symbol = item.account_id, item.symbol
        # Completed previews return their receipt even if the FX provider is down.
        if not item.order_id:
            refresh_order_fx(db, account_id, symbol)
        return confirm_preview(db, data.preview_id, account_id)
    except ValueError as error:
        raise HTTPException(400, str(error))


@router.post("/market", response_model=OrderRead)
def market(order_in: OrderCreate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return _submit(order_in, db, user, execute_market_order)


@router.post("/", response_model=OrderRead)
def create_order(order_in: OrderCreate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return _submit(order_in, db, user, place_order)


@router.post("/process-pending")
def process_pending(account_id: int, limit: int = Query(100, ge=1, le=500), db: Session = Depends(get_db), user: User = Depends(current_user)):
    owned_account(account_id, db, user)
    return process_pending_limit_orders(db, limit=limit, account_id=account_id)


@router.post("/{order_id}/cancel", response_model=OrderRead)
def cancel(order_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    owned_account(order.account_id, db, user)
    try:
        return cancel_order(db, order_id, order.account_id)
    except ValueError as error:
        raise HTTPException(400, str(error))
