"""Observed FX quotes, expressed as account units per one native currency unit."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

import yfinance as yf
import threading
from app.core.config import settings
from sqlalchemy import select
from app.models.models import Account, FxRate, Position, PriceBar
from app.services.currencies import normalize_currency, quote_currency

SUPPORTED_CURRENCIES = {'USD', 'VND'}
MAX_AGE = timedelta(hours=settings.fx_quote_max_age_hours)
_REFRESH_LOCK = threading.Lock()
CACHE_TTL = timedelta(minutes=5)


@dataclass(frozen=True)
class FxQuote:
    rate: Decimal
    timestamp: datetime | None
    source: str


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def money_amount(value, currency):
    return Decimal(value).quantize(Decimal('1') if currency == 'VND' else Decimal('0.0001'), rounding=ROUND_HALF_UP)


def _usable(rate, timestamp):
    now = utcnow()
    return Decimal(rate).is_finite() and Decimal(rate) > 0 and timestamp is not None and now - MAX_AGE <= timestamp <= now + timedelta(minutes=5)


def get_fx_quote(db, from_currency, to_currency):
    source, target = normalize_currency(from_currency), normalize_currency(to_currency)
    if not source or not target:
        raise ValueError('The investment currency is unavailable. Refresh its price before trading.')
    if source == target:
        return FxQuote(Decimal('1'), None, 'same_currency')
    if source not in SUPPORTED_CURRENCIES or target not in SUPPORTED_CURRENCIES:
        raise ValueError(f'Automatic exchange from {source} to {target} is not supported yet.')
    row = db.get(FxRate, (source, target))
    if not row or not _usable(row.rate, row.timestamp):
        raise ValueError(f'A current {source}/{target} exchange rate is unavailable. Please try again.')
    return FxQuote(Decimal(row.rate), row.timestamp, row.source)


def _fetch_usd_vnd():
    ticker = yf.Ticker('USDVND=X')
    history = ticker.history(period='5d', interval='1h', auto_adjust=False, timeout=8)
    if history.empty:
        raise ValueError('No exchange rate observations')
    metadata = ticker.get_history_metadata() or {}
    if metadata.get('currency') != 'VND' or metadata.get('instrumentType') != 'CURRENCY':
        raise ValueError('Invalid exchange rate currency or instrument')
    latest = history.iloc[-1]
    timestamp = latest.name.to_pydatetime()
    if timestamp.tzinfo is not None:
        timestamp = timestamp.astimezone(timezone.utc).replace(tzinfo=None)
    rate = Decimal(str(latest['Close']))
    if not _usable(rate, timestamp):
        raise ValueError('Invalid exchange rate observation')
    return rate, timestamp


def refresh_fx_quote(db, from_currency, to_currency):
    source, target = normalize_currency(from_currency), normalize_currency(to_currency)
    if source == target or source not in SUPPORTED_CURRENCIES or target not in SUPPORTED_CURRENCIES:
        return get_fx_quote(db, source, target)
    row = db.get(FxRate, (source, target))
    if row and _usable(row.rate, row.timestamp) and row.updated_at >= utcnow() - CACHE_TTL:
        return get_fx_quote(db, source, target)
    # Never wait on Yahoo while holding an account/order lock or a read connection.
    db.commit()
    try:
        with _REFRESH_LOCK:
            # Another request or the worker may have refreshed while this one waited.
            cached = db.get(FxRate, (source, target), populate_existing=True)
            if cached and _usable(cached.rate, cached.timestamp) and cached.updated_at >= utcnow() - CACHE_TTL:
                return get_fx_quote(db, source, target)
            db.commit()
            rate, timestamp = _fetch_usd_vnd()
            dialect = db.get_bind().dialect.name
            if dialect == 'postgresql':
                from sqlalchemy.dialects.postgresql import insert
            else:
                from sqlalchemy.dialects.sqlite import insert
            for start, end, observed in [('USD', 'VND', rate), ('VND', 'USD', Decimal('1') / rate)]:
                statement = insert(FxRate).values(from_currency=start, to_currency=end, rate=observed,
                    timestamp=timestamp, source='yfinance:USDVND=X', updated_at=utcnow())
                statement = statement.on_conflict_do_update(index_elements=['from_currency', 'to_currency'],
                    set_={key: getattr(statement.excluded, key) for key in ('rate', 'timestamp', 'source', 'updated_at')})
                db.execute(statement)
            db.commit()
            db.expire_all()
    except Exception:
        db.rollback()
        # A still-valid observed rate may survive a temporary upstream outage.
    return get_fx_quote(db, source, target)


def refresh_order_fx(db, account_id, symbol):
    account = db.get(Account, account_id)
    quote = db.scalars(select(PriceBar).where(PriceBar.symbol == symbol.strip().upper()).order_by(PriceBar.timestamp.desc()).limit(1)).first()
    native = quote_currency(db, quote) if quote else None
    if not account:
        raise ValueError('Paper portfolio not found')
    return refresh_fx_quote(db, native, account.currency)


def refresh_portfolio_fx(db, account_id):
    account = db.get(Account, account_id)
    if not account:
        raise ValueError('Paper portfolio not found')
    target = account.currency
    symbols = list(db.scalars(select(Position.symbol).where(Position.account_id == account_id, Position.quantity > 0)))
    currencies = set()
    for symbol in symbols:
        quote = db.scalars(select(PriceBar).where(PriceBar.symbol == symbol).order_by(PriceBar.timestamp.desc()).limit(1)).first()
        if quote:
            currencies.add(quote_currency(db, quote))
    for source in currencies:
        refresh_fx_quote(db, source, target)
