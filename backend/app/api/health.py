from fastapi import APIRouter, Depends, Request
from sqlalchemy import text, inspect
from fastapi.responses import JSONResponse
from app.db.base import Base
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.migrations import missing_currency_columns

router = APIRouter()

@router.get('/health')
def health(request: Request, db: Session = Depends(get_db)):
    db.execute(text('SELECT 1'))
    if set(Base.metadata.tables) - set(inspect(db.connection()).get_table_names()) or missing_currency_columns(db.connection()):
        return JSONResponse({'status': 'not_ready', 'database': 'schema_setup_required'}, status_code=503)
    worker = getattr(request.app.state, 'paper_worker', None)
    external = getattr(request.app.state, 'external_paper_worker', False)
    return {'status': 'ok', 'database': 'connected', 'paper_trading': worker.status if worker else
            {'enabled': external, 'mode': 'external' if external else 'disabled'}}
