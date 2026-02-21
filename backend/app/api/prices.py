import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi import WebSocket, WebSocketDisconnect
import asyncio
import contextlib
import json
import threading
import time
from datetime import datetime, timezone
import certifi

# Force TLS trust bundle for websocket/https clients on local macOS Python setups.
os.environ.setdefault("SSL_CERT_FILE", certifi.where())
os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())

import yfinance as yf

from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import date

from app.db.session import get_db
from app.core.config import settings
from app.models.models import PriceBar
from app.schemas.prices import PriceBarRead, LoadStockRequest, LoadCryptoRequest
from app.data.price_loader import (
    load_stock_history,
    load_crypto_klines,
    fetch_latest_stock_bar_yfinance,
)
from app.services.price_refresh import _upsert_bar, refresh_watchlist_db



router = APIRouter()

MAX_LIVE_BULK = 5
_LIVE_CACHE_LOCK = threading.Lock()
_LIVE_CACHE: dict[str, tuple[float, dict]] = {}


def _get_live_item(symbol: str, force_refresh: bool = False) -> dict | None:
    ttl = max(1, int(settings.live_price_ttl_seconds))
    now = time.time()

    if not force_refresh:
        with _LIVE_CACHE_LOCK:
            cached = _LIVE_CACHE.get(symbol)
            if cached and (now - cached[0]) <= ttl:
                return cached[1]

    item = fetch_latest_stock_bar_yfinance(symbol)
    if not item:
        return None

    with _LIVE_CACHE_LOCK:
        _LIVE_CACHE[symbol] = (now, item)
    return item


def _fetch_bulk_latest_bars(symbols: list[str]) -> list[dict]:
    out = []
    for s in symbols[:MAX_LIVE_BULK]:
        s_norm = s.strip().upper()
        item = _get_live_item(s_norm)
        if not item:
            continue
        out.append(
            {
                "symbol": s_norm,
                "timestamp": item["timestamp"].isoformat(),
                "close": str(item["close"]),
                "source": item.get("source", "yfinance"),
            }
        )
    return out

@router.post("/load/stock")
def load_stock(req: LoadStockRequest, db: Session = Depends(get_db)):
    try:
        count = load_stock_history(
            db=db,
            symbol=req.symbol,
            start=req.start,
            end=req.end,
            interval=req.interval,
        )
        return {"message": f"Loaded {count} bars for {req.symbol} (yfinance)"}
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
    Fetch latest yfinance bar and upsert into DB, then return latest row.
    """
    s_norm = symbol.strip().upper()
    item = _get_live_item(s_norm, force_refresh=True)
    if item:
        try:
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
        except ValueError:
            db.rollback()

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
    # 1) Try yfinance first (latest bar)
    live_map = {}
    for s in symbols[:MAX_LIVE_BULK]:
        s_norm = s.strip().upper()
        item = _get_live_item(s_norm)
        if item:
            live_map[s_norm] = item

    # 2) Fallback to DB if yfinance didn't return a symbol
    out = []
    touched = []
    for s in symbols:
        s_norm = s.strip().upper()
        item = live_map.get(s_norm)

        if item and item.get("close") is not None:
            try:
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
                        "source": item.get("source", "yfinance"),
                    }
                )
                continue
            except ValueError:
                pass

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

    yws = None

    async def _send_prices(decoded: dict):
        item = _normalize_ws_payload(decoded)
        if not item:
            return
        await ws.send_text(json.dumps({"type": "prices", "data": [item]}))

    try:
        # First message should be config JSON, e.g.:
        # {"symbols":["AAPL","MSFT","SPY"],"interval_ms":1000}
        raw = await ws.receive_text()
        cfg = json.loads(raw)

        symbols = [s.strip().upper() for s in cfg.get("symbols", []) if str(s).strip()]
        if not symbols:
            await ws.send_text(json.dumps({"type": "error", "message": "No symbols provided"}))
            return

        stream_task = None
        if settings.yfinance_ws_enabled:
            try:
                yws = yf.AsyncWebSocket()
                await yws.subscribe(symbols)
                stream_task = asyncio.create_task(yws.listen(_send_prices))
            except Exception as e:
                # Fallback when upstream yfinance websocket cannot connect (TLS, network, etc.)
                await ws.send_text(
                    json.dumps(
                        {
                            "type": "warning",
                            "message": f"yfinance websocket unavailable, using polling fallback: {type(e).__name__}",
                        }
                    )
                )
                stream_task = asyncio.create_task(_poll_and_push(ws, symbols))
        else:
            await ws.send_text(
                json.dumps(
                    {
                        "type": "warning",
                        "message": "yfinance websocket disabled; using polling fallback",
                    }
                )
            )
            stream_task = asyncio.create_task(_poll_and_push(ws, symbols))

        try:
            while True:
                # Wait for client disconnect; any extra client message is ignored.
                await ws.receive_text()
        except WebSocketDisconnect:
            if stream_task:
                stream_task.cancel()
            with contextlib.suppress(Exception):
                if yws is not None:
                    await yws.close()
            return

    except WebSocketDisconnect:
        return
    except Exception as e:
        # best-effort error message; client can decide what to do
        try:
            await ws.send_text(json.dumps({"type": "error", "message": str(e)}))
        except Exception:
            pass
    finally:
        if yws is not None:
            with contextlib.suppress(Exception):
                await yws.close()


def _normalize_ws_payload(decoded: dict) -> dict | None:
    if not isinstance(decoded, dict):
        return None

    symbol = (
        decoded.get("id")
        or decoded.get("symbol")
        or decoded.get("ticker")
    )
    if not symbol:
        return None
    symbol = str(symbol).strip().upper()

    price = (
        decoded.get("price")
        or decoded.get("last_price")
        or decoded.get("regular_market_price")
    )
    if price is None:
        return None

    ts_raw = (
        decoded.get("time")
        or decoded.get("timestamp")
        or decoded.get("regular_market_time")
    )
    ts = _normalize_ws_timestamp(ts_raw)

    return {
        "symbol": symbol,
        "close": str(price),
        "timestamp": ts,
        "source": "yfinance_ws",
    }


def _normalize_ws_timestamp(value) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat()

    if isinstance(value, (int, float)):
        if value > 1e12:
            dt = datetime.fromtimestamp(value / 1000.0, tz=timezone.utc)
        else:
            dt = datetime.fromtimestamp(value, tz=timezone.utc)
        return dt.isoformat()

    try:
        return str(value)
    except Exception:
        return datetime.now(timezone.utc).isoformat()


async def _poll_and_push(ws: WebSocket, symbols: list[str]) -> None:
    while True:
        data = _fetch_bulk_latest_bars(symbols)
        if data:
            await ws.send_text(json.dumps({"type": "prices", "data": data}))
        await asyncio.sleep(2.0)
