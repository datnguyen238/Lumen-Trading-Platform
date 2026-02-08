from fastapi import APIRouter, Depends, HTTPException
from fastapi import WebSocket, WebSocketDisconnect
import asyncio
import json
import anyio

from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime, date

from app.db.session import get_db
from app.core.config import settings
from app.models.models import PriceBar
from app.schemas.prices import PriceBarRead, LoadStockRequest, LoadCryptoRequest
from app.data.price_loader import (
    load_stock_history_polygon,
    load_crypto_klines,
    fetch_latest_stock_bar_polygon,
)
from app.services.price_refresh import _upsert_bar, refresh_watchlist_db



router = APIRouter()

MAX_LIVE_BULK = 5

def _fetch_bulk_latest_bars(symbols: list[str]) -> list[dict]:
    out = []
    for s in symbols[:MAX_LIVE_BULK]:
        s_norm = s.strip().upper()
        item = fetch_latest_stock_bar_polygon(s_norm)
        if not item:
            continue
        out.append(
            {
                "symbol": s_norm,
                "timestamp": item["timestamp"].isoformat(),
                "close": item["close"],
                "source": item.get("source", "rest_agg"),
            }
        )
    return out

@router.post("/load/stock")
def load_stock(req: LoadStockRequest, db: Session = Depends(get_db)):
    try:
        # Polygon uses "day" / "minute" timespans; map your interval if needed.
        # For v1, assume daily bars.
        count = load_stock_history_polygon(
            db=db,
            api_key=settings.polygon_api_key ,
            symbol=req.symbol,
            start=req.start,
            end=req.end,
            timespan="day",
            multiplier=1,
        )
        return {"message": f"Loaded {count} bars for {req.symbol} (Polygon)"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stock load failed: {type(e).__name__}: {e}")




@router.post("/load/crypto")
def load_crypto(req: LoadCryptoRequest, db: Session = Depends(get_db)):
    count = load_crypto_klines(db, req.symbol, req.interval, req.limit)
    return {"message": f"Loaded {count} bars for {req.symbol}"}


@router.get("/latest", response_model=PriceBarRead)
def latest(symbol: str, db: Session = Depends(get_db)):
    row = (
        db.query(PriceBar)
        .filter(PriceBar.symbol == symbol)
        .order_by(desc(PriceBar.timestamp))
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="No data for symbol. Load prices first.")
    return row


@router.post("/refresh", response_model=PriceBarRead)
def refresh(symbol: str, db: Session = Depends(get_db)):
    """
    Fetch latest aggregate bar and upsert into DB, then return latest row.
    """
    s_norm = symbol.strip().upper()
    item = fetch_latest_stock_bar_polygon(s_norm)
    if item:
        row = _upsert_bar(
            db,
            s_norm,
            item["timestamp"],
            item["open"],
            item["high"],
            item["low"],
            item["close"],
            item.get("volume"),
        )
        db.commit()
        db.refresh(row)
        return row

    # Fallback to most recent DB row
    row = (
        db.query(PriceBar)
        .filter(PriceBar.symbol == s_norm)
        .order_by(desc(PriceBar.timestamp))
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="No data for symbol. Load prices first.")
    return row


@router.get("/history", response_model=list[PriceBarRead])
def history(symbol: str, start: date, end: date, db: Session = Depends(get_db)):
    start_ts = datetime.combine(start, datetime.min.time())
    end_ts = datetime.combine(end, datetime.max.time())

    rows = (
        db.query(PriceBar)
        .filter(PriceBar.symbol == symbol, PriceBar.timestamp >= start_ts, PriceBar.timestamp <= end_ts)
        .order_by(PriceBar.timestamp.asc())
        .all()
    )
    if not rows:
        raise HTTPException(status_code=404, detail="No data for symbol/date range.")
    return rows


@router.post("/latest/bulk")
def latest_bulk(symbols: list[str], db: Session = Depends(get_db)):
    # 1) Try Polygon aggregates first (latest bar)
    live_map = {}
    for s in symbols[:MAX_LIVE_BULK]:
        s_norm = s.strip().upper()
        item = fetch_latest_stock_bar_polygon(s_norm)
        if item:
            live_map[s_norm] = item

    # 2) Fallback to DB if Polygon didn't return a symbol
    out = []
    touched = []
    for s in symbols:
        s_norm = s.strip().upper()
        item = live_map.get(s_norm)

        if item and item.get("close") is not None:
            row = _upsert_bar(
                db,
                s_norm,
                item["timestamp"],
                item["open"],
                item["high"],
                item["low"],
                item["close"],
                item.get("volume"),
            )
            touched.append(row)
            out.append(
                {
                    "symbol": s_norm,
                    "timestamp": item.get("timestamp").isoformat(),
                    "close": item.get("close"),
                    "source": item.get("source", "rest_agg"),
                }
            )
            continue

        row = (
            db.query(PriceBar)
            .filter(PriceBar.symbol == s_norm)
            .order_by(desc(PriceBar.timestamp))
            .first()
        )
        if row:
            out.append(
                {
                    "symbol": s_norm,
                    "timestamp": row.timestamp,
                    "close": str(row.close),
                    "source": "db",
                }
            )
        else:
            out.append({"symbol": s_norm, "timestamp": None, "close": None, "source": "none"})

    if touched:
        db.commit()

    return out


@router.post("/refresh/watchlist")
def refresh_watchlist(limit: int = 50, db: Session = Depends(get_db)):
    requested, refreshed, skipped = refresh_watchlist_db(db, limit=limit)
    return {"requested": requested, "refreshed": refreshed, "skipped": skipped}


@router.websocket("/ws/live")
async def ws_live_prices(ws: WebSocket):
    await ws.accept()

    try:
        # First message should be config JSON, e.g.:
        # {"symbols":["AAPL","MSFT","SPY"],"interval_ms":1000}
        raw = await ws.receive_text()
        cfg = json.loads(raw)

        symbols = [s.strip().upper() for s in cfg.get("symbols", []) if str(s).strip()]
        interval_ms = int(cfg.get("interval_ms", 1000))
        interval_ms = max(250, min(interval_ms, 10000))  # clamp 0.25s–10s

        while True:
            # fetch_latest_stock_bar_polygon is blocking, so run in a worker thread
            data = await anyio.to_thread.run_sync(_fetch_bulk_latest_bars, symbols)
            await ws.send_text(json.dumps({"type": "prices", "data": data}))
            await asyncio.sleep(interval_ms / 1000.0)

    except WebSocketDisconnect:
        return
    except Exception as e:
        # best-effort error message; client can decide what to do
        try:
            await ws.send_text(json.dumps({"type": "error", "message": str(e)}))
        except Exception:
            pass
