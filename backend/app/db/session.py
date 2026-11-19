from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings


def _build_engine(url: str):
    connect_args = {}
    pool_options = {}
    if url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    else:
        connect_args = {"connect_timeout": settings.db_connect_timeout_seconds}
        pool_options = {"pool_size": settings.db_pool_size, "max_overflow": settings.db_max_overflow,
                        "pool_timeout": 10, "pool_recycle": 300}
    return create_engine(
        url,
        echo=False,
        future=True,
        connect_args=connect_args,
        pool_pre_ping=True,
        **pool_options,
    )


engine = _build_engine(settings.database_url)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
