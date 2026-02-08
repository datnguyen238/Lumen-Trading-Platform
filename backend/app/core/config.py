from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./trading.db"

    # Your API key (keep this field name – it matches your codebase)
    polygon_api_key: str

    # REST base for Polygon snapshots
    rest_base_url: str = "https://api.polygon.io"

    # Watchlist refresh job
    watchlist_refresh_enabled: bool = True
    watchlist_refresh_interval_seconds: int = 300
    watchlist_refresh_limit: int = 50

    class Config:
        env_file = ".env"


settings = Settings()
