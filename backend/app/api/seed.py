from datetime import date, timedelta
import time

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.data.symbols import DEFAULT_WATCHLIST
from app.data.price_loader import load_stock_history


# IMPORTANT: This must be the SQLAlchemy model (the one in models.py),
# not the Pydantic schema from app.schemas.
from app.models.models import Symbol  # <-- if your file is app/models.py

router = APIRouter()

def upsert_symbol(db: Session, item: dict) -> None:
    sym = str(item.get("symbol", "")).strip().upper()
    if not sym:
        return

    existing = db.query(Symbol).filter(Symbol.symbol == sym).first()
    if existing:
        return

    name = item.get("name")
    asset_type = item.get("asset_type") or item.get("kind") or "stock"

    db.add(
        Symbol(
            symbol=sym,
            name=name,
            asset_type=asset_type,
        )
    )
    db.flush()



@router.post("/seed/default-watchlist")
def seed_default_watchlist(
    load_history: bool = False,
    days: int = 30,
    delay_ms: int = 1200,
    db: Session = Depends(get_db),
):
    start = date.today() - timedelta(days=days)
    end = date.today()

    results = []

    for item in DEFAULT_WATCHLIST:
        symbol = str(item.get("symbol", "")).strip().upper()
        if not symbol:
            continue

        # 1) Insert into symbols table so GET /symbols works
        upsert_symbol(db, item)
        db.commit()


        if symbol.startswith("^"):
            results.append({"symbol": symbol, "bars_loaded": 0, "skipped": "index_symbol"})
            continue

        if load_history:
            # 2) Load price history (yfinance)
            try:
                count = load_stock_history(
                    db=db,
                    symbol=symbol,
                    start=start,
                    end=end,
                    interval="1d",
                )
                db.commit()
                results.append({"symbol": symbol, "bars_loaded": count})
            except Exception as e:
                db.rollback()
                results.append(
                    {"symbol": symbol, "bars_loaded": 0, "skipped": f"{type(e).__name__}: {e}"}
                )
            time.sleep(max(0, delay_ms) / 1000.0)
        else:
            results.append({"symbol": symbol, "bars_loaded": 0, "skipped": "history_disabled"})

    # Commit symbol inserts (and any pending changes)
    db.commit()

    return results
