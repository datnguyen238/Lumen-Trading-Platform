"""A short-lived login-attempt budget shared by autoscaled API instances."""
import hashlib
import ipaddress
import time
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, Request
from app.models.models import AuthRateBucket


def check_attempts(request: Request, db):
    # This header is trusted only by the Vercel-specific caller. Vercel overwrites it.
    address = request.headers.get('x-vercel-forwarded-for', '').split(',')[0].strip()
    try:
        address = str(ipaddress.ip_address(address))
    except ValueError:
        address = request.client.host if request.client else 'unknown'
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    window = int(time.time() // 60)
    key = hashlib.sha256(f'{address}:{window}'.encode()).hexdigest()
    if db.get_bind().dialect.name == 'postgresql':
        from sqlalchemy.dialects.postgresql import insert
    else:
        from sqlalchemy.dialects.sqlite import insert
    statement = insert(AuthRateBucket).values(key=key, attempts=1, expires_at=now+timedelta(minutes=2))
    statement = statement.on_conflict_do_update(index_elements=['key'],
        set_={'attempts': AuthRateBucket.attempts+1}).returning(AuthRateBucket.attempts)
    attempts = db.execute(statement).scalar_one()
    db.query(AuthRateBucket).filter(AuthRateBucket.expires_at < now).delete()
    db.commit()  # Failed credentials cannot roll back their attempt counter.
    if attempts > 15:
        raise HTTPException(429, 'Too many attempts. Wait a minute before trying again.', headers={'Retry-After': '60'})
