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
    df = yf.download(symbol, start=start, end=end, interval=interval, progress=False)
    if df.empty:
        return 0

    df = df.reset_index()
    inserted = 0

    for _, row in df.iterrows():
        ts_raw = row.get("Datetime") or row.get("Date")
        ts = ts_raw.to_pydatetime() if hasattr(ts_raw, "to_pydatetime") else ts_raw

        bar = PriceBar(
            symbol=symbol,
            timestamp=ts,
            open=Decimal(str(row["Open"])),
            high=Decimal(str(row["High"])),
            low=Decimal(str(row["Low"])),
            close=Decimal(str(row["Close"])),
            volume=_maybe_decimal(row.get("Volume")),
        )

        db.add(bar)
        try:
            db.commit()
            inserted += 1
        except IntegrityError:
            db.rollback()

    return inserted


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
