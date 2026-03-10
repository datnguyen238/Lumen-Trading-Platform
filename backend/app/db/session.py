from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings


def _build_engine(url: str):
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    return create_engine(
        url,
        echo=False,
        future=True,
        connect_args=connect_args,
        pool_pre_ping=True,
    )


engine = _build_engine(settings.database_url)
try:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
except Exception as e:
    raise RuntimeError(
        "Database connection failed for configured DATABASE_URL. "
        "Update backend/.env to a single valid database target."
    ) from e

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
