from fastapi import APIRouter, Depends, HTTPException

from fastapi import WebSocket, WebSocketDisconnect
import asyncio
import json
import anyio


from app.data.price_loader import fetch_latest_stock_snapshot

from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime, date
from pydantic import BaseModel

from app.db.session import get_db
from app.core.config import settings
from app.models.models import PriceBar
from app.schemas.prices import PriceBarRead, LoadStockRequest, LoadCryptoRequest
from app.data.price_loader import load_stock_history_polygon, load_crypto_klines



router = APIRouter()
class LatestBulkRequest(BaseModel):
    symbols: list[str]


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
    # 1) Try Polygon snapshot first (live-ish)
    live = fetch_latest_stock_snapshot(symbols)
    live_map = {x["symbol"]: x for x in live if x.get("symbol")}

    # 2) Fallback to DB if Polygon didn't return a symbol
    out = []
    for s in symbols:
        s_norm = s.strip().upper()
        item = live_map.get(s_norm)

        if item and item.get("close") is not None:
            out.append(
                {
                    "symbol": s_norm,
                    "timestamp": item.get("timestamp"),
                    "close": item.get("close"),
                    "source": item.get("source", "rest_snapshot"),
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

    return out


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
            # fetch_latest_stock_snapshot is blocking (requests), so run in a worker thread
            data = await anyio.to_thread.run_sync(fetch_latest_stock_snapshot, symbols)
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
