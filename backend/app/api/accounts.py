from app.services.auth import current_user, owned_account
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.models import User, Account, Position
from app.schemas.accounts import AccountCreate, AccountRead, PositionRead
from app.services.currencies import STARTING_CASH

router = APIRouter()


@router.post("/", response_model=AccountRead)
def create_account(account_in: AccountCreate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if account_in.user_id != user.id:
        raise HTTPException(403, "You can only create your own portfolio.")

    account = Account(user_id=account_in.user_id, name=account_in.name, currency=account_in.currency, cash_balance=STARTING_CASH[account_in.currency])
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.get("/{account_id}", response_model=AccountRead)
def get_account(account_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    acc = owned_account(account_id, db, user)
    return acc


@router.get("/{account_id}/positions", response_model=list[PositionRead])
def get_positions(account_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    acc = owned_account(account_id, db, user)
    return db.query(Position).filter(Position.account_id == account_id).all()
