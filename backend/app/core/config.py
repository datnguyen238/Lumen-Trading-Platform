from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)
    vercel: bool = False
    vercel_env: str = ""
    vercel_url: str = ""
    vercel_project_production_url: str = ""
    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/lumen_trading"
    migration_database_url: str | None = None
    database_auto_setup: bool = True
    db_pool_size: int = Field(default=2, ge=1, le=20)
    db_max_overflow: int = Field(default=0, ge=0, le=20)
    db_connect_timeout_seconds: int = Field(default=10, ge=1, le=60)
    yfinance_ws_enabled: bool = True
    live_price_ttl_seconds: int = 300
    history_cache_ttl_seconds: int = 300
    live_bulk_limit: int = 50
    frontend_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    session_cookie_secure: bool | None = None
    session_days: int = 7
    paper_worker_enabled: bool = True
    paper_worker_interval_seconds: int = 30
    paper_worker_symbol_limit: int = 30
    fx_quote_max_age_hours: int = Field(default=72, ge=1, le=168)
    execution_quote_max_age_days: int = 7
    preview_expiry_seconds: int = 120

    # Watchlist refresh job
    watchlist_refresh_enabled: bool = False
    watchlist_refresh_interval_seconds: int = 300
    watchlist_refresh_limit: int = 50

    @property
    def secure_cookies(self) -> bool:
        return self.vercel or bool(self.session_cookie_secure)

    @property
    def embedded_worker_enabled(self) -> bool:
        return self.paper_worker_enabled and not self.vercel

    @property
    def allowed_origins(self) -> set[str]:
        origins = {value.strip().rstrip("/") for value in self.frontend_origins.split(",") if value.strip()}
        if self.vercel:
            origins = {value for value in origins if value.startswith("https://")}
            for host in (self.vercel_url, self.vercel_project_production_url):
                if host and "/" not in host and ":" not in host:
                    origins.add(f"https://{host}")
        return origins

    @model_validator(mode="after")
    def validate_hosted_database(self):
        if self.vercel and ("localhost" in self.database_url or "127.0.0.1" in self.database_url or self.database_url.startswith("sqlite")):
            raise ValueError("Set DATABASE_URL to the Supabase PostgreSQL pooler URL in the Vercel project environment.")
        return self


settings = Settings()
