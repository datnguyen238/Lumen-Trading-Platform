from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models.models import PriceBar


def get_last_close(db: Session, symbol: str) -> Decimal:
    symbol = str(symbol).strip().upper()
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
    symbol = str(symbol).strip().upper()
    row = (
        db.query(PriceBar)
        .filter(PriceBar.symbol == symbol)
        .order_by(desc(PriceBar.timestamp))
        .first()
    )
    if not row:
        raise ValueError(f"No price data for '{symbol}'")
    return Decimal(row.close)


def get_execution_quote(db: Session, symbol: str) -> PriceBar:
    """Valuations may display old prices; execution requires a usable observation."""
    from datetime import datetime, timedelta, timezone
    from app.core.config import settings
    if symbol.startswith('^'):
        raise ValueError('Indices are market references. Choose a stock or fund to trade.')
    row = db.query(PriceBar).filter(PriceBar.symbol == symbol.strip().upper()).order_by(PriceBar.timestamp.desc()).first()
    if not row:
        raise ValueError('No price is available yet. Refresh this investment before trading.')
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if row.timestamp < now - timedelta(days=settings.execution_quote_max_age_days):
        raise ValueError('This quote is too old to trade. Refresh the price and review your order again.')
    if row.timestamp > now + timedelta(minutes=5):
        raise ValueError('The quote time is invalid. Refresh the price before trading.')
    if not Decimal(row.close).is_finite() or row.close <= 0:
        raise ValueError('A valid market price is needed before trading.')
    return row


def refresh_execution_quote(db: Session, symbol: str):
    # Release read/identity transactions before waiting on the market-data provider.
    # Callers run this before creating or mutating any order.
    db.commit()
    from app.data.price_loader import fetch_latest_stock_bar_yfinance
    from app.services.price_refresh import _upsert_bar
    item = fetch_latest_stock_bar_yfinance(symbol)
    if item:
        _upsert_bar(db, symbol, item['timestamp'], item['open'], item['high'], item['low'], item['close'], item.get('volume'))
        db.commit()
    return get_execution_quote(db, symbol)
