"""Keep application sessions and portfolios private on Supabase's public schema."""
from sqlalchemy import text

PRIVATE_TABLES = ('users', 'accounts', 'positions', 'orders', 'trades', 'user_credentials',
                  'auth_sessions', 'order_receipts', 'order_previews', 'execution_details', 'saved_assets', 'auth_rate_buckets')


def protect_private_tables(engine):
    if engine.dialect.name != 'postgresql':
        return
    with engine.begin() as connection:
        roles = set(connection.execute(text("SELECT rolname FROM pg_roles WHERE rolname IN ('anon', 'authenticated')")).scalars())
        # Names below come from fixed application constants, never request input.
        for table in PRIVATE_TABLES:
            enabled = connection.execute(text("SELECT relrowsecurity FROM pg_class WHERE oid=to_regclass(:table)"), {'table': table}).scalar()
            if not enabled:
                connection.execute(text(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY'))
            for role in roles:
                connection.execute(text(f'REVOKE ALL ON TABLE "{table}" FROM "{role}"'))
