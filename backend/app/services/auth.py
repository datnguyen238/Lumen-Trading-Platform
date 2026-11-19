import hashlib
import hmac
import secrets
from datetime import datetime

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.models import Account, AuthSession, User

COOKIE_NAME = "lumen_session"


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=2**15,
                            r=8, p=3, maxmem=64 * 1024 * 1024).hex()
    return f"scrypt${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt, _ = stored.split("$")
        return hmac.compare_digest(hash_password(password, salt), stored)
    except (ValueError, TypeError):
        return False


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def current_session(request: Request, db: Session = Depends(get_db)) -> AuthSession:
    token = request.cookies.get(COOKIE_NAME, "")
    session = db.get(AuthSession, token_hash(token)) if token else None
    if not session or session.expires_at <= datetime.utcnow():
        raise HTTPException(401, "Sign in to continue with your paper portfolio.")
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        csrf = request.headers.get("X-CSRF-Token", "")
        if not csrf or not hmac.compare_digest(csrf, session.csrf_token):
            raise HTTPException(403, "Your session needs refreshing. Reload the page and try again.")
    return session


def current_user(session: AuthSession = Depends(current_session), db: Session = Depends(get_db)) -> User:
    user = db.get(User, session.user_id)
    if not user:
        raise HTTPException(401, "Sign in again to continue.")
    return user


def owned_account(account_id: int, db: Session, user: User) -> Account:
    account = db.query(Account).filter(Account.id == account_id, Account.user_id == user.id).first()
    if not account:
        raise HTTPException(404, "Paper portfolio not found.")
    return account
