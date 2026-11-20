"""Read-only preflight for hosted runtime configuration and database schema."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import inspect, text
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine
from app.models import models  # noqa: F401
from app.db.migrations import missing_currency_columns


def main():
    failures = []
    with engine.connect() as connection:
        connection.execute(text('SELECT 1'))
        missing = set(Base.metadata.tables) - set(inspect(connection).get_table_names())
        if missing:
            failures.append('Missing tables: ' + ', '.join(sorted(missing)) + '. Run python -m app.db.bootstrap.')
        columns = missing_currency_columns(connection)
        if columns:
            failures.append('Missing currency columns: ' + ', '.join(columns) + '. Run python -m app.db.bootstrap.')
        if connection.dialect.name == 'postgresql':
            from app.db.privacy import PRIVATE_TABLES
            for name in PRIVATE_TABLES:
                enabled = connection.execute(text('SELECT relrowsecurity FROM pg_class WHERE oid=to_regclass(:name)'), {'name': name}).scalar()
                if not enabled:
                    failures.append(f'Privacy rules need setup on {name}. Run the bootstrap command.')
    if settings.vercel:
        if not settings.secure_cookies:
            failures.append('HTTPS session cookies are required.')
        if settings.embedded_worker_enabled:
            failures.append('The API must not run an embedded matcher on Vercel.')
        if not any(origin.startswith('https://') for origin in settings.allowed_origins):
            failures.append('Set FRONTEND_ORIGINS to the exact HTTPS site URL.')
    for failure in failures:
        print('FAIL', failure)
    if failures:
        return 1
    print('PASS database connection, schema, privacy, and runtime configuration')
    print('Worker mode:', 'external daemon' if settings.vercel else 'local embedded')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
