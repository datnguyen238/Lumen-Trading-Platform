from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.models import User, Account, Position
from app.schemas.accounts import AccountCreate, AccountRead, PositionRead

router = APIRouter()


@router.post("/", response_model=AccountRead)
def create_account(account_in: AccountCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == account_in.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    account = Account(user_id=account_in.user_id, name=account_in.name)
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.get("/{account_id}", response_model=AccountRead)
def get_account(account_id: int, db: Session = Depends(get_db)):
    acc = db.query(Account).filter(Account.id == account_id).first()
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")
    return acc


@router.get("/{account_id}/positions", response_model=list[PositionRead])
def get_positions(account_id: int, db: Session = Depends(get_db)):
    acc = db.query(Account).filter(Account.id == account_id).first()
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")
    return db.query(Position).filter(Position.account_id == account_id).all()
