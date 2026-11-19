from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.models import SavedAsset, User
from app.services.auth import current_user

router = APIRouter(prefix='/watchlist', tags=['watchlist'])
SymbolPath = Path(min_length=1, max_length=20, pattern=r'^[A-Za-z^][A-Za-z0-9.^=\-]{0,19}$')


def symbols(db, user):
    return [row.symbol for row in db.query(SavedAsset).filter(SavedAsset.user_id == user.id).order_by(SavedAsset.created_at, SavedAsset.symbol)]


@router.get('')
def get_watchlist(db: Session = Depends(get_db), user: User = Depends(current_user)) -> list[str]:
    return symbols(db, user)


@router.put('/{symbol}')
def save_asset(symbol: str = SymbolPath, db: Session = Depends(get_db), user: User = Depends(current_user)) -> list[str]:
    if db.get_bind().dialect.name == 'postgresql':
        from sqlalchemy.dialects.postgresql import insert
    else:
        from sqlalchemy.dialects.sqlite import insert
    statement = insert(SavedAsset).values(user_id=user.id, symbol=symbol.upper())
    db.execute(statement.on_conflict_do_nothing(index_elements=['user_id', 'symbol']))
    db.commit()
    return symbols(db, user)


@router.delete('/{symbol}')
def remove_asset(symbol: str = SymbolPath, db: Session = Depends(get_db), user: User = Depends(current_user)) -> list[str]:
    db.query(SavedAsset).filter(SavedAsset.user_id == user.id, SavedAsset.symbol == symbol.upper()).delete()
    db.commit()
    return symbols(db, user)
