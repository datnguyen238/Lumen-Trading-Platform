from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import yfinance as yf

from app.db.session import get_db
from app.models.models import Symbol
from app.schemas.symbols import SymbolAddRequest, SymbolRead

router = APIRouter()


@router.get("/symbols", response_model=list[SymbolRead])
def list_symbols(db: Session = Depends(get_db)):
    return db.query(Symbol).order_by(Symbol.symbol.asc()).all()


@router.post("/symbols/add", response_model=SymbolRead)
def add_symbol(req: SymbolAddRequest, db: Session = Depends(get_db)):
    sym = req.symbol.strip().upper()

    existing = db.query(Symbol).filter(Symbol.symbol == sym).first()
    if existing:
        return existing

    # Validate symbol using yfinance: if no recent data, reject
    try:
        t = yf.Ticker(sym)
        hist = t.history(period="5d", interval="1d")
        if hist.empty:
            raise HTTPException(status_code=400, detail="Invalid symbol or no data found.")
        name = None
        try:
            fi = getattr(t, "fast_info", None)
            # fast_info doesn't always include a name; fallback to None
            _ = fi
        except Exception:
            pass
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"yfinance error: {str(e)}")

    row = Symbol(symbol=sym, name=name, asset_type=req.asset_type)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
