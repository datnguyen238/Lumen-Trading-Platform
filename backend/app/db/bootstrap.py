"""Explicit, additive database setup; never runs as a Vercel request hook."""
from app.core.config import settings
from app.db.base import Base
from app.db.session import _build_engine
from app.db.privacy import protect_private_tables
from app.models import models  # noqa: F401 - register metadata


def main():
    engine = _build_engine(settings.migration_database_url or settings.database_url)
    try:
        Base.metadata.create_all(bind=engine)
        protect_private_tables(engine)
    finally:
        engine.dispose()
    print('Database tables and privacy rules are ready. Existing records were preserved.')


if __name__ == '__main__':
    main()
