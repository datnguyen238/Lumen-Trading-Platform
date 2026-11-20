from sqlalchemy.orm import Session
from decimal import Decimal

from app.models.models import Account, Position, Trade, Order, PriceBar
from app.models.enums import OrderStatus
from app.services.execution import available_resources
from app.models.enums import OrderSide
from app.schemas.summary import AccountSummary, SymbolPnL
from app.services.fx import get_fx_quote, money_amount
from app.services.currencies import require_currency


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
        price = t.account_price
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


def build_summary(db: Session, acc: Account) -> AccountSummary:
    account_id = acc.id

    positions = db.query(Position).filter(Position.account_id == account_id).all()

    cash = Decimal(acc.cash_balance)
    realized_total = _compute_realized_pnl(db, account_id)
    unrealized_total = Decimal("0")
    market_value_total = Decimal("0")
    out_positions = {}
    pending = db.query(Order).filter(Order.account_id == account_id, Order.status == OrderStatus.PENDING).all()
    reserved_cash = sum((money_amount((Decimal(o.quantity) - Decimal(o.filled_quantity)) * Decimal(o.limit_price or 0) * Decimal(o.fx_rate), acc.currency)
                         for o in pending if o.side == OrderSide.BUY), Decimal(0))

    for p in positions:
        qty = Decimal(p.quantity)
        if qty == 0:
            continue

        avg_cost = Decimal(p.average_price)
        quote = db.query(PriceBar).filter(PriceBar.symbol == p.symbol).order_by(PriceBar.timestamp.desc()).first()
        if not quote:
            raise ValueError(f'No price data for {p.symbol}. Refresh the investment.')
        native_currency = require_currency(db, acc, quote)
        fx = get_fx_quote(db, native_currency, acc.currency)
        mark = Decimal(quote.close) * fx.rate
        market_value = mark * qty
        unrealized = (mark - avg_cost) * qty
        market_value_total += market_value
        unrealized_total += unrealized

        out_positions[p.symbol] = SymbolPnL(
            symbol=p.symbol,
            currency=acc.currency, native_currency=native_currency, native_mark_price=Decimal(quote.close),
            fx_rate=fx.rate, fx_timestamp=fx.timestamp, fx_source=fx.source,
            quantity=qty,
            avg_cost=avg_cost,
            mark_price=mark,
            market_value=market_value,
            unrealized_pnl=unrealized,
            available_quantity=available_resources(db, acc, p.symbol)[1],
            reserved_quantity=qty-available_resources(db, acc, p.symbol)[1],
        )

    # Net liquidation value: cash + current marked value of open positions
    equity = cash + market_value_total

    return AccountSummary(
        account_id=account_id,
        currency=acc.currency,
        cash=cash,
        reserved_cash=reserved_cash,
        available_cash=max(Decimal(0), cash-reserved_cash),
        equity=equity,
        market_value=market_value_total,
        realized_pnl=realized_total,
        unrealized_pnl=unrealized_total,
        total_pnl=realized_total + unrealized_total,
        positions=out_positions,
    )
