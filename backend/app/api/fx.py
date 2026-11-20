from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.fx import refresh_fx_quote

router = APIRouter()

@router.get('/fx/quote')
def fx_quote(from_currency: str = Query(min_length=3, max_length=3), to_currency: str = Query(min_length=3, max_length=3), db: Session = Depends(get_db)):
    try:
        quote = refresh_fx_quote(db, from_currency, to_currency)
        return {'from_currency': from_currency.upper(), 'to_currency': to_currency.upper(), 'rate': str(quote.rate),
            'timestamp': quote.timestamp, 'source': quote.source}
    except ValueError as error:
        raise HTTPException(503, str(error)) from None
