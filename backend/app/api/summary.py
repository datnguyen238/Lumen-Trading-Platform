from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.models import User
from app.schemas.summary import AccountSummary
from app.services.auth import current_user, owned_account
from app.services.portfolio import build_summary

router = APIRouter()

@router.get("/accounts/{account_id}/summary", response_model=AccountSummary)
def account_summary(account_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    account = owned_account(account_id, db, user)
    try:
        return build_summary(db, account)
    except ValueError as error:
        raise HTTPException(409, str(error)) from None
