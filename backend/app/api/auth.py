import secrets
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.models import Account, AuthSession, User, UserCredential
from app.schemas.accounts import AccountRead
from app.schemas.users import UserRead
from app.services.auth import COOKIE_NAME, current_session, hash_password, token_hash, verify_password
from app.services.currencies import AccountCurrency, STARTING_CASH

router = APIRouter(prefix="/auth", tags=["auth"])
_attempts: dict[str, deque] = defaultdict(deque)
_lock = threading.Lock()
# Spend the same hashing work for unknown accounts.
_dummy_hash = hash_password(secrets.token_urlsafe(32))


class Login(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class Signup(Login):
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=100)
    currency: AccountCurrency = 'USD'


class SessionRead(BaseModel):
    user: UserRead
    accounts: list[AccountRead]
    csrf_token: str


def _check_attempts(request: Request, db: Session):
    if settings.vercel:
        from app.services.login_throttle import check_attempts
        return check_attempts(request, db)
    # Local-process protection; configure a shared limiter for multiple workers.
    key = request.client.host if request.client else "unknown"
    now = time.monotonic()
    with _lock:
        for stale in list(_attempts):
            if not _attempts[stale] or _attempts[stale][-1] < now - 60:
                del _attempts[stale]
        attempts = _attempts[key]
        while attempts and attempts[0] < now - 60:
            attempts.popleft()
        if len(attempts) >= 15:
            raise HTTPException(429, "Too many attempts. Wait a minute before trying again.")
        attempts.append(now)


def _payload(db: Session, session: AuthSession) -> dict:
    return {"user": db.get(User, session.user_id),
            "accounts": db.query(Account).filter(Account.user_id == session.user_id).order_by(Account.id).all(),
            "csrf_token": session.csrf_token}


def _start(db: Session, user: User, request: Request, response: Response) -> dict:
    old = request.cookies.get(COOKIE_NAME)
    if old:
        previous = db.get(AuthSession, token_hash(old))
        if previous:
            db.delete(previous)
    db.query(AuthSession).filter(AuthSession.expires_at <= datetime.utcnow()).delete()
    token = secrets.token_urlsafe(32)
    session = AuthSession(token_hash=token_hash(token), user_id=user.id, csrf_token=secrets.token_hex(32),
                          expires_at=datetime.utcnow() + timedelta(days=settings.session_days))
    db.add(session)
    db.commit()
    response.set_cookie(COOKIE_NAME, token, httponly=True, secure=settings.secure_cookies,
                        samesite="lax", max_age=settings.session_days * 86400, path="/")
    response.headers["Cache-Control"] = "no-store"
    return _payload(db, session)


@router.post("/signup", response_model=SessionRead)
def signup(body: Signup, request: Request, response: Response, db: Session = Depends(get_db)):
    _check_attempts(request, db)
    email = str(body.email).strip().lower()
    if db.query(User).filter(func.lower(User.email) == email).first():
        raise HTTPException(409, "This email is already in use. Sign in, or use another email for a new practice account.")
    if not body.full_name.strip():
        raise HTTPException(422, "Enter your name.")
    user = User(email=email, full_name=body.full_name.strip())
    try:
        db.add(user)
        db.flush()
        db.add(UserCredential(user_id=user.id, password_hash=hash_password(body.password)))
        db.add(Account(user_id=user.id, name="My portfolio", currency=body.currency, cash_balance=STARTING_CASH[body.currency]))
        return _start(db, user, request, response)
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "This email is already in use. Sign in or try another email.")


@router.post("/login", response_model=SessionRead)
def login(body: Login, request: Request, response: Response, db: Session = Depends(get_db)):
    _check_attempts(request, db)
    user = db.query(User).filter(func.lower(User.email) == str(body.email).strip().lower()).first()
    credential = db.get(UserCredential, user.id) if user else None
    valid = verify_password(body.password, credential.password_hash if credential else _dummy_hash)
    if not credential or not valid:
        raise HTTPException(401, "Email or password doesn’t match. Check both and try again.")
    return _start(db, user, request, response)


@router.get("/me", response_model=SessionRead)
def me(response: Response, session: AuthSession = Depends(current_session), db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    return _payload(db, session)


@router.post("/logout")
def logout(response: Response, session: AuthSession = Depends(current_session), db: Session = Depends(get_db)):
    db.delete(session)
    db.commit()
    response.delete_cookie(COOKIE_NAME, path="/", secure=settings.secure_cookies, httponly=True, samesite="lax")
    return {"message": "Signed out"}
