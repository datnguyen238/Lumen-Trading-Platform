from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session
import yfinance as yf

from app.db.session import get_db
from app.models.models import Symbol
from app.schemas.symbols import SymbolAddRequest, SymbolRead, SymbolSearchRead
from app.services.symbol_search import search_market_symbols
from app.services.currencies import known_currency, normalize_currency

router = APIRouter()


def _resolve_company_name(ticker: yf.Ticker) -> str | None:
    try:
        info = ticker.info or {}
        for key in ("shortName", "longName", "displayName", "name"):
            value = info.get(key)
            if value:
                return str(value).strip()
    except Exception:
        pass
    return None


@router.get("/symbols", response_model=list[SymbolRead])
def list_symbols(db: Session = Depends(get_db)):
    return db.query(Symbol).order_by(Symbol.symbol.asc()).all()


@router.get('/symbols/search', response_model=list[SymbolSearchRead])
def search_symbols(q: str = Query(min_length=2, max_length=80), db: Session = Depends(get_db)):
    query = ' '.join(q.split())
    if len(query) < 2:
        return []
    known = db.query(Symbol).filter(or_(Symbol.symbol.icontains(query, autoescape=True),
        Symbol.name.icontains(query, autoescape=True))).order_by(Symbol.symbol).limit(8).all()
    items = {item.symbol: {'symbol': item.symbol, 'name': item.name, 'asset_type': item.asset_type,
                          'currency': item.currency or known_currency(item.symbol), 'exchange': item.exchange} for item in known}
    db.rollback()  # Release the read connection while waiting on the external provider.
    try:
        for item in search_market_symbols(query):
            items[item['symbol']] = {**items.get(item['symbol'], {}), **{key: value for key, value in item.items() if value is not None}}
    except Exception:
        if not items:
            raise HTTPException(503, 'Market search is temporarily unavailable. Please try again.') from None
    return sorted(items.values(), key=lambda item: (item['symbol'] != query.upper(), item['symbol']))[:8]


@router.post("/symbols/add", response_model=SymbolRead)
def add_symbol(req: SymbolAddRequest, db: Session = Depends(get_db)):
    sym = req.symbol.strip().upper()

    existing = db.query(Symbol).filter(Symbol.symbol == sym).first()
    if existing:
        if not existing.name or not existing.currency:
            try:
                ticker = yf.Ticker(sym)
                name = _resolve_company_name(ticker)
                if name:
                    existing.name = name
                metadata = ticker.get_history_metadata() or {}
                existing.currency = normalize_currency(metadata.get('currency')) or known_currency(sym)
                existing.exchange = metadata.get('exchangeName')
                db.commit()
                db.refresh(existing)
            except Exception:
                pass
        return existing

    # Validate symbol using yfinance: if no recent data, reject
    try:
        t = yf.Ticker(sym)
        hist = t.history(period="5d", interval="1d", timeout=8)
        if hist.empty:
            raise HTTPException(status_code=400, detail="No market data is available for this ticker. Search by company name or listed symbol.")
        name = _resolve_company_name(t)
        metadata = t.get_history_metadata() or {}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=503, detail="Market data is temporarily unavailable. Please try again.") from None

    row = Symbol(symbol=sym, name=name, asset_type=req.asset_type,
                 currency=normalize_currency(metadata.get('currency')) or known_currency(sym),
                 exchange=metadata.get('exchangeName'))
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
