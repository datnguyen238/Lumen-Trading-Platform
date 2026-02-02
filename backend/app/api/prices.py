from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime, date
from app.models.models import PriceBar

from app.db.session import get_db
from app.models.models import PriceBar
from app.schemas.prices import PriceBarRead, LoadStockRequest, LoadCryptoRequest
from app.data.price_loader import load_stock_history, load_crypto_klines



router = APIRouter()


@router.post("/load/stock")
def load_stock(req: LoadStockRequest, db: Session = Depends(get_db)):
    try:
        count = load_stock_history(db, req.symbol, req.start, req.end, req.interval)
        return {"message": f"Loaded {count} bars for {req.symbol}"}
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
    out = []
    for s in symbols:
        row = (
            db.query(PriceBar)
            .filter(PriceBar.symbol == s)
            .order_by(desc(PriceBar.timestamp))
            .first()
        )
        if row:
            out.append({
                "symbol": s,
                "timestamp": row.timestamp,
                "close": str(row.close),
            })
        else:
            out.append({
                "symbol": s,
                "timestamp": None,
                "close": None,
            })
    return out
