"""Atomic, long-only paper execution with reserved cash/shares and retry receipts."""
import hashlib
from decimal import Decimal
from sqlalchemy.orm import Session

from app.models.models import Account, Order, OrderReceipt, Trade, Position, ExecutionDetail
from app.models.enums import OrderSide, OrderStatus, OrderType
from app.schemas.orders import OrderCreate
from app.services.pricing import get_execution_quote
from app.services.positions import apply_fill
from app.services.currencies import require_currency
from app.services.fx import get_fx_quote, money_amount, refresh_order_fx


def _account(db, account_id):
    account = db.query(Account).filter(Account.id == account_id).populate_existing().with_for_update().first()
    if not account:
        raise ValueError("Paper portfolio not found")
    return account


def _fingerprint(data):
    values = [data.symbol.strip().upper(), data.side.value, data.order_type.value,
              str(Decimal(data.quantity).normalize()),
              str(Decimal(data.limit_price).normalize()) if data.limit_price is not None else ""]
    return hashlib.sha256("|".join(values).encode()).hexdigest()


def _existing(db, data):
    if not data.client_order_id:
        return None
    receipt = db.get(OrderReceipt, (data.account_id, data.client_order_id))
    if receipt:
        if receipt.fingerprint != _fingerprint(data):
            raise ValueError("This order reference was already used. Start a new order.")
        return db.get(Order, receipt.order_id)
    return None


def _receipt(db, data, order):
    if data.client_order_id:
        db.add(OrderReceipt(account_id=data.account_id, request_key=data.client_order_id,
                            fingerprint=_fingerprint(data), order_id=order.id))


def available_resources(db, account, symbol, exclude_order_id=None):
    pending = db.query(Order).filter(Order.account_id == account.id, Order.status == OrderStatus.PENDING).all()
    reserved_cash = Decimal(0)
    reserved_shares = Decimal(0)
    for item in pending:
        if item.id == exclude_order_id:
            continue
        remaining = Decimal(item.quantity) - Decimal(item.filled_quantity)
        if item.side == OrderSide.BUY:
            reserved_cash += money_amount(remaining * Decimal(item.limit_price or 0) * Decimal(item.fx_rate), account.currency)
        elif item.symbol == symbol:
            reserved_shares += remaining
    pos = db.query(Position).filter(Position.account_id == account.id, Position.symbol == symbol).populate_existing().first()
    owned = Decimal(pos.quantity) if pos else Decimal(0)
    return max(Decimal(0), Decimal(account.cash_balance) - reserved_cash), max(Decimal(0), owned - reserved_shares)


def _check(db, account, symbol, side, qty, price, exclude=None, quote=None, fx=None):
    currency = require_currency(db, account, quote if quote is not None else get_execution_quote(db, symbol))
    if not price.is_finite() or price <= 0:
        raise ValueError("A valid market price is needed before trading.")
    if currency == 'VND' and qty != qty.to_integral_value():
        raise ValueError('Vietnamese stocks use whole shares. Enter a whole number of shares.')
    if currency == 'VND' and price != price.to_integral_value():
        raise ValueError('Enter a price in whole VND.')
    fx = fx or get_fx_quote(db, currency, account.currency)
    total = money_amount(qty * price * fx.rate, account.currency)
    minimum = Decimal('1') if account.currency == 'VND' else Decimal('0.01')
    if side == OrderSide.BUY and total < minimum:
        raise ValueError(f'The trade value must be at least {minimum} {account.currency}. Increase the amount or shares.')
    cash, shares = available_resources(db, account, symbol, exclude)
    if side == OrderSide.BUY and total > cash:
        raise ValueError("Insufficient cash balance. Reduce the amount or cancel an open buy order.")
    if side == OrderSide.SELL and qty > shares:
        raise ValueError("Insufficient position quantity. Reduce the shares or cancel an open sell order.")
    return fx


def _fill(db, account, order, quote):
    price = Decimal(quote.close)
    qty = Decimal(order.quantity) - Decimal(order.filled_quantity or 0)
    native = require_currency(db, account, quote)
    if (order.native_currency or account.currency) != native:
        raise ValueError('The investment currency changed. Cancel this order and review it again.')
    fx = _check(db, account, order.symbol, order.side, qty, price, order.id, quote=quote)
    total = money_amount(qty * price * fx.rate, account.currency)
    cash_before = Decimal(account.cash_balance)
    apply_fill(db, account, order.symbol, order.side, qty, price * fx.rate)
    snapshot = dict(native_currency=native, fx_rate=fx.rate, fx_timestamp=fx.timestamp, fx_source=fx.source)
    db.add(ExecutionDetail(order_id=order.id, quote_timestamp=quote.timestamp, quote_price=price,
                           cash_before=cash_before, cash_after=account.cash_balance, fees=0, account_value=total, **snapshot))
    db.add(Trade(account_id=account.id, order_id=order.id, symbol=order.symbol,
                 side=order.side, quantity=qty, price=price, account_value=total, **snapshot))
    for key, value in snapshot.items():
        setattr(order, key, value)
    order.filled_quantity = order.quantity
    order.avg_fill_price = price
    order.status = OrderStatus.FILLED
    db.flush()


def execute_market_order(db: Session, order_in: OrderCreate) -> Order:
    if order_in.order_type != OrderType.MARKET:
        raise ValueError("Choose MARKET for an immediate paper trade.")
    return place_order(db, order_in)


def place_order(db: Session, order_in: OrderCreate, preview=None, execution_quote=None) -> Order:
    try:
        account = _account(db, order_in.account_id)
        previous = _existing(db, order_in)
        if previous:
            db.commit()  # Release the account lock even for a retry.
            return previous
        symbol = order_in.symbol.strip().upper()
        qty = Decimal(order_in.quantity)
        quote = execution_quote if execution_quote is not None else get_execution_quote(db, symbol)
        mark = Decimal(quote.close)
        if order_in.order_type == OrderType.LIMIT and order_in.limit_price is None:
            raise ValueError("Enter a limit price for this order.")
        price = Decimal(order_in.limit_price) if order_in.order_type == OrderType.LIMIT else mark
        fx = _check(db, account, symbol, order_in.side, qty, price, quote=quote)
        native = require_currency(db, account, quote)
        order = Order(account_id=account.id, symbol=symbol, side=order_in.side,
                      order_type=order_in.order_type, quantity=qty, limit_price=order_in.limit_price,
                      status=OrderStatus.PENDING, filled_quantity=0, native_currency=native,
                      fx_rate=fx.rate, fx_timestamp=fx.timestamp, fx_source=fx.source)
        db.add(order)
        db.flush()
        crosses = order.side == OrderSide.BUY and mark <= price or order.side == OrderSide.SELL and mark >= price
        if order.order_type == OrderType.MARKET or crosses:
            _fill(db, account, order, quote)
        if preview is not None:
            preview.order_id = order.id
        _receipt(db, order_in, order)
        db.commit()
        db.refresh(order)
        return order
    except Exception:
        db.rollback()
        raise


def cancel_order(db: Session, order_id: int, account_id: int | None = None) -> Order:
    if account_id is None:
        raise ValueError("Select a paper portfolio first.")
    try:
        _account(db, account_id)
        order = db.query(Order).filter(Order.id == order_id, Order.account_id == account_id).populate_existing().with_for_update().first()
        if not order:
            raise ValueError("Order not found")
        if order.status != OrderStatus.PENDING:
            raise ValueError("This order is already closed. Refresh activity for its latest status.")
        order.status = OrderStatus.CANCELED
        db.commit()
        db.refresh(order)
        return order
    except Exception:
        db.rollback()
        raise


def process_pending_limit_orders(db: Session, symbol: str | None = None, limit: int = 100, account_id: int | None = None) -> dict:
    query = db.query(Order).filter(Order.order_type == OrderType.LIMIT, Order.status == OrderStatus.PENDING)
    if symbol:
        query = query.filter(Order.symbol == symbol.strip().upper())
    if account_id is not None:
        query = query.filter(Order.account_id == account_id)
    orders = [(o.id, o.account_id) for o in query.order_by(Order.account_id, Order.created_at, Order.id).limit(max(1, min(limit, 500))).all()]
    filled = 0
    if orders:
        refreshes = [(owner, db.get(Order, order_id).symbol) for order_id, owner in orders]
        for owner, investment in dict.fromkeys(refreshes):
            try:
                refresh_order_fx(db, owner, investment)
            except ValueError:
                db.rollback()
    for order_id, owner in orders:
        try:
            # A rejected fill must roll back every cash/position mutation for that order.
            with db.begin_nested():
                account = _account(db, owner)
                order = db.query(Order).filter(Order.id == order_id).populate_existing().with_for_update().one()
                if order.status != OrderStatus.PENDING:
                    continue
                quote = get_execution_quote(db, order.symbol)
                # Never grant a resting order a fill using a price observed before it existed.
                if quote.timestamp <= order.created_at:
                    continue
                mark = Decimal(quote.close)
                target = Decimal(order.limit_price)
                if (order.side == OrderSide.BUY and mark <= target) or (order.side == OrderSide.SELL and mark >= target):
                    _fill(db, account, order, quote)
                    filled += 1
        except ValueError:
            continue
    db.commit()
    return {"processed": len(orders), "filled": filled, "skipped": len(orders) - filled}
