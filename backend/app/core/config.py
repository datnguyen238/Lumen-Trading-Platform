from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/lumen_trading"
    yfinance_ws_enabled: bool = True
    live_price_ttl_seconds: int = 300
    history_cache_ttl_seconds: int = 300
    live_bulk_limit: int = 50

    # Watchlist refresh job
    watchlist_refresh_enabled: bool = False
    watchlist_refresh_interval_seconds: int = 300
    watchlist_refresh_limit: int = 50

    class Config:
        env_file = ".env"


settings = Settings()
