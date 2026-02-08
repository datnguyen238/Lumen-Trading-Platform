from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.data.price_loader import fetch_latest_stock_bar_polygon
from app.models.models import PriceBar, Symbol


def _upsert_bar(
    db: Session,
    symbol: str,
    ts: datetime,
    open_v: str | float | int,
    high_v: str | float | int,
    low_v: str | float | int,
    close_v: str | float | int,
    volume_v: str | float | int | None,
) -> PriceBar:
    o = Decimal(str(open_v))
    h = Decimal(str(high_v))
    l = Decimal(str(low_v))
    c = Decimal(str(close_v))
    v = Decimal(str(volume_v)) if volume_v is not None else None

    existing = (
        db.query(PriceBar)
        .filter(PriceBar.symbol == symbol, PriceBar.timestamp == ts)
        .first()
    )
    if existing:
        existing.open = o
        existing.high = h
        existing.low = l
        existing.close = c
        existing.volume = v
        return existing

    row = PriceBar(
        symbol=symbol,
        timestamp=ts,
        open=o,
        high=h,
        low=l,
        close=c,
        volume=v,
    )
    db.add(row)
    return row


def refresh_watchlist_db(db: Session, limit: int = 50) -> tuple[int, int, int]:
    symbols = (
        db.query(Symbol)
        .order_by(Symbol.id.asc())
        .limit(limit)
        .all()
    )

    refreshed = 0
    skipped = 0

    for sym in symbols:
        item = fetch_latest_stock_bar_polygon(sym.symbol)
        if not item:
            skipped += 1
            continue
        _upsert_bar(
            db,
            sym.symbol,
            item["timestamp"],
            item["open"],
            item["high"],
            item["low"],
            item["close"],
            item.get("volume"),
        )
        refreshed += 1

    if refreshed:
        db.commit()

    return len(symbols), refreshed, skipped
