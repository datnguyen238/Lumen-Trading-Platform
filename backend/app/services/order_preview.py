"""Server-owned reviews: one preview can create at most one order."""
import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.enums import OrderSide, OrderType
from app.models.models import OrderPreview, Order, Position
from app.schemas.orders import OrderCreate, PreviewRead, PreviewRequest
from app.services.execution import _account, _check, available_resources, place_order
from app.services.pricing import get_execution_quote


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _shares(budget, price):
    return (Decimal(budget) / Decimal(price)).quantize(Decimal('0.0001'), rounding=ROUND_DOWN)


def create_preview(db: Session, request: PreviewRequest) -> PreviewRead:
    symbol = request.symbol.strip().upper()
    quote = get_execution_quote(db, symbol)
    account = _account(db, request.account_id)
    price = Decimal(request.limit_price) if request.order_type == OrderType.LIMIT else Decimal(quote.close)
    qty = _shares(request.notional, price) if request.notional is not None else request.quantity
    if qty <= 0:
        raise ValueError('Choose an amount that buys at least 0.0001 shares.')
    _check(db, account, symbol, request.side, qty, price)
    cash, shares = available_resources(db, account, symbol)
    position = db.query(Position).filter(Position.account_id == account.id, Position.symbol == symbol).first()
    owned = Decimal(position.quantity) if position else Decimal(0)
    cash_before = Decimal(account.cash_balance)
    total = (qty * price).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
    direction = 1 if request.side == OrderSide.BUY else -1
    preview = OrderPreview(id=secrets.token_hex(24), account_id=account.id, symbol=symbol,
        side=request.side, order_type=request.order_type, quantity=qty, notional=request.notional,
        limit_price=request.limit_price, quoted_price=price, quote_timestamp=quote.timestamp,
        expires_at=utcnow() + timedelta(seconds=settings.preview_expiry_seconds))
    db.add(preview)
    db.commit()
    explanation = ('A market order practices buying or selling at the latest available price. Dollar buys never exceed your chosen budget.'
        if request.order_type == OrderType.MARKET else
        'A limit buy fills at your price or lower; a limit sell fills at your price or higher. Cash or shares are reserved until filled or canceled.')
    return PreviewRead(id=preview.id, account_id=account.id, symbol=symbol, side=request.side,
        order_type=request.order_type, quantity=qty, notional=request.notional, limit_price=request.limit_price,
        estimated_price=price, estimated_total=total, quote_timestamp=quote.timestamp, expires_at=preview.expires_at,
        cash_before=cash_before, cash_after=cash_before-direction*total, shares_before=owned,
        shares_after=owned+direction*qty, available_cash=cash, available_shares=shares, explanation=explanation)


def confirm_preview(db: Session, preview_id: str, account_id: int) -> Order:
    try:
        _account(db, account_id)
        preview = db.query(OrderPreview).filter(OrderPreview.id == preview_id, OrderPreview.account_id == account_id).populate_existing().with_for_update().first()
        if not preview:
            raise ValueError('This trade review could not be found. Review your order again.')
        if preview.order_id:
            order = db.get(Order, preview.order_id)
            db.commit()
            return order
        if preview.expires_at <= utcnow():
            raise ValueError('This trade review expired. Edit your order and review the latest price again.')
        quote = get_execution_quote(db, preview.symbol)
        qty = _shares(preview.notional, quote.close) if preview.notional is not None else Decimal(preview.quantity)
        if qty <= 0:
            raise ValueError('The latest price needs a larger dollar amount. Review your order again.')
        data = OrderCreate(account_id=account_id, symbol=preview.symbol, side=preview.side,
            order_type=preview.order_type, quantity=qty, limit_price=preview.limit_price, client_order_id=preview.id)
        return place_order(db, data, preview=preview, execution_quote=quote)
    except Exception:
        db.rollback()
        raise
