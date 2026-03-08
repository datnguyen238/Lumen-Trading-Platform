from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings

def _build_engine(url: str):
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    return create_engine(url, echo=False, future=True, connect_args=connect_args)


try:
    engine = _build_engine(settings.database_url)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
except Exception as e:
    print(f"[db] primary connection failed: {e}")
    print(f"[db] falling back to {settings.database_fallback_url}")
    engine = _build_engine(settings.database_fallback_url)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
