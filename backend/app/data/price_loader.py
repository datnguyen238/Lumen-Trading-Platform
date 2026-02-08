from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.models import PriceBar
from polygon import RESTClient
from app.core.config import settings


BINANCE_BASE_URL = "https://api.binance.com"
_AGG_CACHE: dict[str, tuple[datetime, dict]] = {}
_AGG_TTL_SECONDS = 300


# def load_stock_history(db: Session, symbol: str, start: date, end: date, interval: str = "1d") -> int:
#     import pandas as pd

#     df = yf.download(symbol, start=start, end=end, interval=interval, progress=False)
#     if df.empty:
#         return 0
#     # yfinance sometimes returns MultiIndex columns like ('Open','AAPL').
#     # Flatten to single-level so row["Open"] is a scalar.
#     if hasattr(df.columns, "levels"):  # MultiIndex
#         df.columns = df.columns.get_level_values(0)


#     df = df.reset_index()
#     inserted_or_updated = 0

#     for _, row in df.iterrows():
#         ts_raw = row.get("Datetime") or row.get("Date")
#         ts = ts_raw.to_pydatetime() if hasattr(ts_raw, "to_pydatetime") else ts_raw

#         # Force naive datetime (drop timezone) to avoid SQLite issues
#         if getattr(ts, "tzinfo", None) is not None:
#             ts = ts.replace(tzinfo=None)

#         # Skip bad rows (NaN OHLC)
#         o, h, l, c = row.get("Open"), row.get("High"), row.get("Low"), row.get("Close")
#         if pd.isna(o) or pd.isna(h) or pd.isna(l) or pd.isna(c):
#             continue

#         open_ = Decimal(str(o))
#         high_ = Decimal(str(h))
#         low_ = Decimal(str(l))
#         close_ = Decimal(str(c))
#         volume_ = _maybe_decimal(row.get("Volume"))

#         # Upsert-style: update if exists, else insert
#         existing = (
#             db.query(PriceBar)
#             .filter(PriceBar.symbol == symbol, PriceBar.timestamp == ts)
#             .first()
#         )

#         if existing:
#             existing.open = open_
#             existing.high = high_
#             existing.low = low_
#             existing.close = close_
#             existing.volume = volume_
#         else:
#             db.add(
#                 PriceBar(
#                     symbol=symbol,
#                     timestamp=ts,
#                     open=open_,
#                     high=high_,
#                     low=low_,
#                     close=close_,
#                     volume=volume_,
#                 )
#             )

#         inserted_or_updated += 1

#     db.commit()
#     return inserted_or_updated


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
    """
    Backwards-compatible name used by seed.py.
    Uses Polygon/Massive REST aggregates via polygon-api-client.
    """
    # Map your interval to Polygon aggregates parameters
    if interval == "1d":
        timespan, multiplier = "day", 1
    elif interval in ("1m", "1min", "1minute"):
        timespan, multiplier = "minute", 1
    else:
        raise ValueError(f"Unsupported interval: {interval}")

    return load_stock_history_polygon(
        db=db,
        api_key=settings.polygon_api_key,
        symbol=symbol,
        start=start,
        end=end,
        timespan=timespan,
        multiplier=multiplier,
    )



def load_stock_history_polygon(db: Session, api_key: str, symbol: str, start: date, end: date, timespan: str = "day", multiplier: int = 1) -> int:
    """
    Loads OHLCV from Polygon aggregates into PriceBar.
    Uses: /v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{from}/{to}  (via RESTClient)
    """
    client = RESTClient(api_key)

    inserted_or_updated = 0

    # polygon-api-client returns objects with fields like:
    # o, h, l, c, v, t (t is ms timestamp)
    aggs = client.list_aggs(
        ticker=symbol,
        multiplier=multiplier,
        timespan=timespan,
        from_=start.isoformat(),
        to=end.isoformat(),
        limit=50000,
    )

    for a in aggs:
        ts = datetime.utcfromtimestamp(a.timestamp / 1000.0)

        existing = (
            db.query(PriceBar)
            .filter(PriceBar.symbol == symbol, PriceBar.timestamp == ts)
            .first()
        )

        if existing:
            existing.open = Decimal(str(a.open))
            existing.high = Decimal(str(a.high))
            existing.low = Decimal(str(a.low))
            existing.close = Decimal(str(a.close))
            existing.volume = Decimal(str(a.volume)) if a.volume is not None else None
        else:
            db.add(
                PriceBar(
                    symbol=symbol,
                    timestamp=ts,
                    open=Decimal(str(a.open)),
                    high=Decimal(str(a.high)),
                    low=Decimal(str(a.low)),
                    close=Decimal(str(a.close)),
                    volume=Decimal(str(a.volume)) if a.volume is not None else None,
                )
            )

        inserted_or_updated += 1

    db.commit()
    return inserted_or_updated

def fetch_latest_stock_bar_polygon(symbol: str) -> dict | None:
    """
    Returns latest aggregate bar using Polygon REST aggregates.
    Shape: {symbol, timestamp, open, high, low, close, volume}
    """
    cached = _AGG_CACHE.get(symbol)
    if cached:
        cached_at, cached_item = cached
        if (datetime.utcnow() - cached_at).total_seconds() < _AGG_TTL_SECONDS:
            return cached_item

    client = RESTClient(settings.polygon_api_key)
    end = date.today()
    start = end - timedelta(days=7)

    try:
        aggs = list(
            client.list_aggs(
            ticker=symbol,
            multiplier=1,
            timespan="day",
            from_=start.isoformat(),
            to=end.isoformat(),
            limit=50000,
            )
        )
    except Exception:
        return cached_item if cached else None

    latest = aggs[-1] if aggs else None

    if not latest:
        return cached_item if cached else None

    ts = datetime.utcfromtimestamp(latest.timestamp / 1000.0)
    item = {
        "symbol": symbol,
        "timestamp": ts,
        "open": latest.open,
        "high": latest.high,
        "low": latest.low,
        "close": latest.close,
        "volume": latest.volume,
        "source": "rest_agg",
    }
    _AGG_CACHE[symbol] = (datetime.utcnow(), item)
    return item
