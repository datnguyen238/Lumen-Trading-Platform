from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional
import math

import requests
import yfinance as yf
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.models import PriceBar


BINANCE_BASE_URL = "https://api.binance.com"
_STOCK_CACHE: dict[str, tuple[datetime, dict]] = {}
_STOCK_TTL_SECONDS = 300


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
    df = yf.download(
        yf_symbol,
        start=start,
        end=end + timedelta(days=1),
        interval=interval,
        progress=False,
        auto_adjust=False,
    )
    if df.empty:
        return 0

    if hasattr(df.columns, "levels"):
        df.columns = df.columns.get_level_values(0)

    df = df.reset_index()
    inserted_or_updated = 0

    for _, row in df.iterrows():
        ts_raw = row.get("Datetime") or row.get("Date")
        ts = ts_raw.to_pydatetime() if hasattr(ts_raw, "to_pydatetime") else ts_raw
        if getattr(ts, "tzinfo", None) is not None:
            ts = ts.replace(tzinfo=None)

        o, h, l, c = row.get("Open"), row.get("High"), row.get("Low"), row.get("Close")
        if any(v is None for v in (o, h, l, c)):
            continue

        open_ = Decimal(str(o))
        high_ = Decimal(str(h))
        low_ = Decimal(str(l))
        close_ = Decimal(str(c))
        volume_ = _maybe_decimal(row.get("Volume"))

        existing = (
            db.query(PriceBar)
            .filter(PriceBar.symbol == symbol, PriceBar.timestamp == ts)
            .first()
        )

        if existing:
            existing.open = open_
            existing.high = high_
            existing.low = low_
            existing.close = close_
            existing.volume = volume_
        else:
            db.add(
                PriceBar(
                    symbol=symbol,
                    timestamp=ts,
                    open=open_,
                    high=high_,
                    low=low_,
                    close=close_,
                    volume=volume_,
                )
            )

        inserted_or_updated += 1

    db.commit()
    return inserted_or_updated


def fetch_latest_stock_bar_yfinance(symbol: str) -> dict | None:
    symbol = str(symbol).strip().upper()
    if not symbol:
        return None

    cached = _STOCK_CACHE.get(symbol)
    if cached:
        cached_at, cached_item = cached
        if (datetime.utcnow() - cached_at).total_seconds() < _STOCK_TTL_SECONDS:
            return cached_item

    yf_symbol = _to_yfinance_symbol(symbol)

    # Prefer most-recent intraday bar when available for better UX on quote refresh.
    # Falls back to daily bar for symbols/markets with limited intraday access.
    latest = None
    try:
        intraday = yf.Ticker(yf_symbol).history(period="2d", interval="1m", auto_adjust=False, prepost=False)
        if not intraday.empty:
            latest = intraday.iloc[-1]
    except Exception:
        latest = None

    if latest is None:
        end = date.today()
        start = end - timedelta(days=7)
        try:
            df = yf.download(
                yf_symbol,
                start=start,
                end=end + timedelta(days=1),
                interval="1d",
                progress=False,
                auto_adjust=False,
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
        ts = ts.replace(tzinfo=None)

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
