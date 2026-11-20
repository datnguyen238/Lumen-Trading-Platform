from datetime import datetime, date, timedelta, timezone
from collections import OrderedDict
from decimal import Decimal
from typing import Optional
import math
from pathlib import Path
import tempfile
from threading import Lock
from time import monotonic
from zoneinfo import ZoneInfo

import requests
import yfinance as yf
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.models import PriceBar
from app.core.config import settings
from app.services.currencies import known_currency, normalize_currency
from app.schemas.prices import DailyPriceRead, PriceRangeRead


if settings.vercel:
    # Hosted functions can only persist temporary cache files under /tmp.
    yf.set_tz_cache_location(str(Path(tempfile.gettempdir()) / "lumen-yfinance"))


BINANCE_BASE_URL = "https://api.binance.com"
_STOCK_CACHE: dict[str, tuple[datetime, dict]] = {}
_STOCK_TTL_SECONDS = 300
_DAILY_STOCK_CACHE: OrderedDict[str, tuple[float, DailyPriceRead]] = OrderedDict()
_DAILY_STOCK_CACHE_LOCK = Lock()
_DAILY_STOCK_CACHE_SIZE = 128
_DAILY_STOCK_TTL_SECONDS = 300
_PRICE_RANGE_CACHE: OrderedDict[tuple[str, int], tuple[float, PriceRangeRead]] = OrderedDict()
_PRICE_RANGE_CACHE_LOCK = Lock()
_PRICE_RANGE_CACHE_SIZE = 128
_PRICE_RANGE_TTL_SECONDS = 300
_PRICE_RANGE_DAYS = (7, 30, 90, 180, 365)


def _market_metadata(ticker, symbol: str) -> dict:
    try:
        metadata = ticker.get_history_metadata() or {}
    except Exception:
        metadata = {}
    return {'currency': normalize_currency(metadata.get('currency')) or known_currency(symbol),
            'exchange': metadata.get('exchangeName')}


def fetch_daily_stock_bar_yfinance(symbol: str) -> DailyPriceRead:
    """Read the latest daily session independently of stored intraday quotes."""
    symbol = str(symbol).strip().upper()
    if not symbol:
        raise ValueError("A ticker is required")

    with _DAILY_STOCK_CACHE_LOCK:
        cached = _DAILY_STOCK_CACHE.get(symbol)
        if cached and monotonic() - cached[0] < _DAILY_STOCK_TTL_SECONDS:
            _DAILY_STOCK_CACHE.move_to_end(symbol)
            return cached[1]
        _DAILY_STOCK_CACHE.pop(symbol, None)

    ticker = yf.Ticker(_to_yfinance_symbol(symbol))
    history = ticker.history(period="5d", interval="1d", auto_adjust=False, timeout=8)
    if history.empty:
        raise ValueError("No daily price observations")
    if hasattr(history.columns, "levels"):
        history = history.copy()
        history.columns = history.columns.get_level_values(0)
    latest = history.sort_index().iloc[-1]
    timestamp = latest.name.to_pydatetime() if hasattr(latest.name, "to_pydatetime") else latest.name
    # A Vietnamese midnight daily bar has a timestamp on the previous UTC day.
    # Capture the exchange's session date before normalizing the timestamp.
    session_date = timestamp.date()
    if getattr(timestamp, "tzinfo", None) is not None:
        timestamp = timestamp.astimezone(timezone.utc).replace(tzinfo=None)

    volume = latest.get("Volume")
    item = DailyPriceRead(
        symbol=symbol,
        currency=_market_metadata(ticker, symbol)["currency"],
        session_date=session_date,
        timestamp=timestamp,
        open=Decimal(str(latest.get("Open"))),
        high=Decimal(str(latest.get("High"))),
        low=Decimal(str(latest.get("Low"))),
        close=Decimal(str(latest.get("Close"))),
        volume=_maybe_decimal(volume) if _is_finite_number(volume) else None,
    )
    with _DAILY_STOCK_CACHE_LOCK:
        _DAILY_STOCK_CACHE[symbol] = (monotonic(), item)
        _DAILY_STOCK_CACHE.move_to_end(symbol)
        while len(_DAILY_STOCK_CACHE) > _DAILY_STOCK_CACHE_SIZE:
            _DAILY_STOCK_CACHE.popitem(last=False)
    return item


def fetch_stock_price_range_yfinance(symbol: str, days: int) -> PriceRangeRead:
    """Aggregate daily highs/lows across the last N exchange-local calendar dates.

    The current local date and the preceding N-1 dates are included. Returned
    dates describe actual observations, including partial listing histories.
    """
    symbol = str(symbol).strip().upper()
    if not symbol or days not in _PRICE_RANGE_DAYS:
        raise ValueError("A ticker and a supported history range are required")
    key = (symbol, days)
    with _PRICE_RANGE_CACHE_LOCK:
        cached = _PRICE_RANGE_CACHE.get(key)
        if cached and monotonic() < cached[0]:
            _PRICE_RANGE_CACHE.move_to_end(key)
            return cached[1]
        _PRICE_RANGE_CACHE.pop(key, None)

    # Fetch a padded UTC window, then filter by the feed's market-local dates.
    # The padding includes today's session on either side of the date line.
    request_date = datetime.now(timezone.utc).date()
    ticker = yf.Ticker(_to_yfinance_symbol(symbol))
    history = ticker.history(
        start=request_date - timedelta(days=days + 2),
        end=request_date + timedelta(days=2),
        interval="1d", auto_adjust=False, keepna=True, timeout=8,
    )
    if history.empty:
        raise ValueError("No daily price observations for this range")
    if hasattr(history.columns, "levels"):
        history = history.copy()
        history.columns = history.columns.get_level_values(0)
    index_tz = getattr(history.index, "tz", None)
    if index_tz is None:
        raise ValueError("Daily price observations have no market timezone")
    market_tz = ZoneInfo(str(index_tz))
    today = datetime.now(timezone.utc).astimezone(market_tz).date()
    cutoff = today - timedelta(days=days - 1)
    bars = []
    seen_dates = set()
    for index, row in history.sort_index().iterrows():
        timestamp = index.to_pydatetime() if hasattr(index, "to_pydatetime") else index
        session_date = timestamp.date()
        if not cutoff <= session_date <= today:
            continue
        if session_date in seen_dates:
            raise ValueError("Duplicate daily price observations")
        seen_dates.add(session_date)
        # Validate every in-window bar; ignoring an invalid day could hide the
        # true high/low while presenting an apparently complete range.
        bars.append(DailyPriceRead(
            symbol=symbol, session_date=session_date, timestamp=timestamp,
            open=Decimal(str(row.get("Open"))), high=Decimal(str(row.get("High"))),
            low=Decimal(str(row.get("Low"))), close=Decimal(str(row.get("Close"))),
        ))
    if not bars:
        raise ValueError("No daily price observations for this range")
    item = PriceRangeRead(
        symbol=symbol, currency=_market_metadata(ticker, symbol)["currency"], days=days,
        window_start_date=cutoff, window_end_date=today, timezone=market_tz.key,
        start_date=bars[0].session_date, end_date=bars[-1].session_date,
        low=min(bar.low for bar in bars), high=max(bar.high for bar in bars),
        observations=len(bars),
    )
    # Never keep the previous calendar window through the market's midnight.
    next_midnight = datetime.combine(today + timedelta(days=1), datetime.min.time(), tzinfo=market_tz)
    ttl = min(_PRICE_RANGE_TTL_SECONDS, (next_midnight - datetime.now(timezone.utc)).total_seconds())
    if ttl > 0:
        with _PRICE_RANGE_CACHE_LOCK:
            _PRICE_RANGE_CACHE[key] = (monotonic() + ttl, item)
            _PRICE_RANGE_CACHE.move_to_end(key)
            while len(_PRICE_RANGE_CACHE) > _PRICE_RANGE_CACHE_SIZE:
                _PRICE_RANGE_CACHE.popitem(last=False)
    return item


def load_crypto_klines(db: Session, symbol: str, interval: str = "1d", limit: int = 500) -> int:
    url = f"{BINANCE_BASE_URL}/api/v3/klines"
    resp = requests.get(url, params={"symbol": symbol, "interval": interval, "limit": limit}, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    inserted = 0
    for k in data:
        ts = datetime.utcfromtimestamp(k[0] / 1000.0)

        bar = PriceBar(
            symbol=symbol,
            currency='USDT' if symbol.upper().endswith('USDT') else None,
            timestamp=ts,
            open=Decimal(k[1]),
            high=Decimal(k[2]),
            low=Decimal(k[3]),
            close=Decimal(k[4]),
            volume=Decimal(k[5]),
        )

        db.add(bar)
        try:
            db.commit()
            inserted += 1
        except IntegrityError:
            db.rollback()

    return inserted


def _maybe_decimal(v) -> Optional[Decimal]:
    if v is None:
        return None
    try:
        return Decimal(str(v))
    except Exception:
        return None


def load_stock_history(db: Session, symbol: str, start: date, end: date, interval: str = "1d") -> int:
    symbol = str(symbol).strip().upper()
    if not symbol:
        return 0

    yf_symbol = _to_yfinance_symbol(symbol)
    ticker = yf.Ticker(yf_symbol)
    df = ticker.history(
        start=start,
        end=end + timedelta(days=1),
        interval=interval,
        auto_adjust=False,
        timeout=10,
    )
    if df.empty:
        return 0
    metadata = _market_metadata(ticker, symbol)
    from app.services.price_refresh import update_instrument_metadata
    update_instrument_metadata(db, symbol, metadata)

    if hasattr(df.columns, "levels"):
        df.columns = df.columns.get_level_values(0)

    df = df.reset_index()
    inserted_or_updated = 0

    for _, row in df.iterrows():
        ts_raw = row.get("Datetime") or row.get("Date")
        ts = ts_raw.to_pydatetime() if hasattr(ts_raw, "to_pydatetime") else ts_raw
        if getattr(ts, "tzinfo", None) is not None:
            ts = ts.astimezone(timezone.utc).replace(tzinfo=None)

        o, h, l, c = row.get("Open"), row.get("High"), row.get("Low"), row.get("Close")
        if any(v is None for v in (o, h, l, c)):
            continue

        open_ = Decimal(str(o))
        high_ = Decimal(str(h))
        low_ = Decimal(str(l))
        close_ = Decimal(str(c))
        volume_ = _maybe_decimal(row.get("Volume"))

        from app.services.price_refresh import _upsert_bar
        try:
            _upsert_bar(db, symbol, ts, open_, high_, low_, close_, volume_, currency=metadata['currency'])
        except ValueError:
            continue

        inserted_or_updated += 1

    db.commit()
    return inserted_or_updated


def fetch_latest_stock_bar_yfinance(symbol: str, force_refresh: bool = False) -> dict | None:
    symbol = str(symbol).strip().upper()
    if not symbol:
        return None

    cached = _STOCK_CACHE.get(symbol)
    if cached and not force_refresh:
        cached_at, cached_item = cached
        if (datetime.utcnow() - cached_at).total_seconds() < _STOCK_TTL_SECONDS:
            return cached_item

    yf_symbol = _to_yfinance_symbol(symbol)
    ticker = yf.Ticker(yf_symbol)

    # Prefer most-recent intraday bar when available for better UX on quote refresh.
    # Falls back to daily bar for symbols/markets with limited intraday access.
    latest = None
    try:
        intraday = ticker.history(period="2d", interval="1m", auto_adjust=False, prepost=False, timeout=10)
        if not intraday.empty:
            latest = intraday.iloc[-1]
    except Exception:
        latest = None

    if latest is None:
        end = date.today()
        start = end - timedelta(days=7)
        try:
            df = ticker.history(
                start=start,
                end=end + timedelta(days=1),
                interval="1d",
                auto_adjust=False,
                timeout=10,
            )
        except Exception:
            return cached[1] if cached else None

        if df.empty:
            return cached[1] if cached else None

        if hasattr(df.columns, "levels"):
            df.columns = df.columns.get_level_values(0)

        latest = df.iloc[-1]

    ts = latest.name.to_pydatetime() if hasattr(latest.name, "to_pydatetime") else latest.name
    if getattr(ts, "tzinfo", None) is not None:
        ts = ts.astimezone(timezone.utc).replace(tzinfo=None)

    o = latest.get("Open")
    h = latest.get("High")
    l = latest.get("Low")
    c = latest.get("Close")
    v = latest.get("Volume")

    # Skip invalid rows (common for unsupported tickers/empty market data days)
    if not _is_finite_number(o) or not _is_finite_number(h) or not _is_finite_number(l) or not _is_finite_number(c):
        return cached[1] if cached else None

    item = {
        "symbol": symbol,
        "timestamp": ts,
        "open": o,
        "high": h,
        "low": l,
        "close": c,
        "volume": v if _is_finite_number(v) else None,
        "source": "yfinance",
        **_market_metadata(ticker, symbol),
    }
    _STOCK_CACHE[symbol] = (datetime.utcnow(), item)
    return item


def _to_yfinance_symbol(symbol: str) -> str:
    # Keep API symbol storage normalized (e.g. ^DJI), but use yfinance ticker format.
    if symbol.startswith("^"):
        return symbol
    return symbol


def _is_finite_number(v) -> bool:
    try:
        n = float(v)
        return math.isfinite(n)
    except Exception:
        return False
