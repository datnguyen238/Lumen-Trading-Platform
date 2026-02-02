from datetime import datetime, date
from decimal import Decimal
from typing import Optional

import yfinance as yf
import requests
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.models import PriceBar

BINANCE_BASE_URL = "https://api.binance.com"


def load_stock_history(db: Session, symbol: str, start: date, end: date, interval: str = "1d") -> int:
    import pandas as pd

    df = yf.download(symbol, start=start, end=end, interval=interval, progress=False)
    if df.empty:
        return 0
    # yfinance sometimes returns MultiIndex columns like ('Open','AAPL').
    # Flatten to single-level so row["Open"] is a scalar.
    if hasattr(df.columns, "levels"):  # MultiIndex
        df.columns = df.columns.get_level_values(0)


    df = df.reset_index()
    inserted_or_updated = 0

    for _, row in df.iterrows():
        ts_raw = row.get("Datetime") or row.get("Date")
        ts = ts_raw.to_pydatetime() if hasattr(ts_raw, "to_pydatetime") else ts_raw

        # Force naive datetime (drop timezone) to avoid SQLite issues
        if getattr(ts, "tzinfo", None) is not None:
            ts = ts.replace(tzinfo=None)

        # Skip bad rows (NaN OHLC)
        o, h, l, c = row.get("Open"), row.get("High"), row.get("Low"), row.get("Close")
        if pd.isna(o) or pd.isna(h) or pd.isna(l) or pd.isna(c):
            continue

        open_ = Decimal(str(o))
        high_ = Decimal(str(h))
        low_ = Decimal(str(l))
        close_ = Decimal(str(c))
        volume_ = _maybe_decimal(row.get("Volume"))

        # Upsert-style: update if exists, else insert
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
