from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./trading.db"

    # Watchlist refresh job
    watchlist_refresh_enabled: bool = True
    watchlist_refresh_interval_seconds: int = 300
    watchlist_refresh_limit: int = 50

    class Config:
        env_file = ".env"


settings = Settings()
