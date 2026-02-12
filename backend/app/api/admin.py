from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import date, timedelta
import time

from app.db.session import get_db
from app.models.models import Trade, Order, Position, Account, User, Symbol, PriceBar
from app.data.symbols import DEFAULT_WATCHLIST
from app.data.price_loader import load_stock_history

router = APIRouter(prefix="/admin")

def _reset_core(db: Session, keep_prices: bool) -> dict:
    deleted_trades = db.query(Trade).delete(synchronize_session=False)
    deleted_orders = db.query(Order).delete(synchronize_session=False)
    deleted_positions = db.query(Position).delete(synchronize_session=False)
    deleted_accounts = db.query(Account).delete(synchronize_session=False)
    deleted_users = db.query(User).delete(synchronize_session=False)
    deleted_symbols = db.query(Symbol).delete(synchronize_session=False)
    deleted_prices = 0
    if not keep_prices:
        deleted_prices = db.query(PriceBar).delete(synchronize_session=False)
    db.commit()

    try:
        db.execute(text("DELETE FROM sqlite_sequence"))
        db.commit()
    except Exception:
        db.rollback()

    return {
        "trades": deleted_trades,
        "orders": deleted_orders,
        "positions": deleted_positions,
        "accounts": deleted_accounts,
        "users": deleted_users,
        "symbols": deleted_symbols,
        "price_bars": deleted_prices,
    }


def _upsert_symbol(db: Session, item: dict) -> Symbol | None:
    sym = str(item.get("symbol", "")).strip().upper()
    if not sym:
        return None
    existing = db.query(Symbol).filter(Symbol.symbol == sym).first()
    if existing:
        return existing
    row = Symbol(
        symbol=sym,
        name=item.get("name"),
        asset_type=item.get("asset_type") or item.get("kind") or item.get("type") or "stock",
    )
    db.add(row)
    db.flush()
    return row


@router.post("/reset-db")
def reset_db(
    confirm: bool = Query(False, description="Must be true to execute reset"),
    keep_prices: bool = Query(True, description="Keep price_bars table data"),
    db: Session = Depends(get_db),
):
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Reset not executed. Pass confirm=true to run.",
        )

    try:
        deleted = _reset_core(db, keep_prices=keep_prices)

        return {
            "message": "Database reset completed",
            "keep_prices": keep_prices,
            "deleted": deleted,
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Reset failed: {type(e).__name__}: {e}")


@router.post("/reset-and-seed")
def reset_and_seed(
    confirm: bool = Query(False, description="Must be true to execute reset and seed"),
    keep_prices: bool = Query(True, description="Keep existing price_bars rows"),
    load_history: bool = Query(False, description="Load recent history for seeded symbols"),
    days: int = Query(30, ge=1, le=365),
    delay_ms: int = Query(1000, ge=0, le=10000),
    db: Session = Depends(get_db),
):
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Reset+seed not executed. Pass confirm=true to run.",
        )

    try:
        deleted = _reset_core(db, keep_prices=keep_prices)
        seeded = []
        start = date.today() - timedelta(days=days)
        end = date.today()

        for item in DEFAULT_WATCHLIST:
            sym_row = _upsert_symbol(db, item)
            if not sym_row:
                continue

            result = {"symbol": sym_row.symbol, "history_loaded": 0}
            if load_history:
                try:
                    count = load_stock_history(
                        db=db,
                        symbol=sym_row.symbol,
                        start=start,
                        end=end,
                        interval="1d",
                    )
                    result["history_loaded"] = count
                except Exception as e:
                    result["skipped"] = f"{type(e).__name__}: {e}"
                time.sleep(delay_ms / 1000.0)
            seeded.append(result)

        db.commit()
        return {
            "message": "Database reset and seed completed",
            "keep_prices": keep_prices,
            "load_history": load_history,
            "deleted": deleted,
            "seeded_count": len(seeded),
            "seeded": seeded,
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Reset+seed failed: {type(e).__name__}: {e}")
