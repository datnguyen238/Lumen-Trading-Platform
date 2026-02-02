from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models.models import PriceBar


def get_last_close(db: Session, symbol: str) -> Decimal:
    row = (
        db.query(PriceBar)
        .filter(PriceBar.symbol == symbol)
        .order_by(desc(PriceBar.timestamp))
        .first()
    )
    if not row:
        raise ValueError(f"No price data for symbol '{symbol}'. Load prices first.")
    return Decimal(row.close)

def get_mark_price(db: Session, symbol: str) -> Decimal:
    row = (
        db.query(PriceBar)
        .filter(PriceBar.symbol == symbol)
        .order_by(desc(PriceBar.timestamp))
        .first()
    )
    if not row:
        raise ValueError(f"No price data for '{symbol}'")
    return Decimal(row.close)

