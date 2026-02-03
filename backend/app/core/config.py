from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./trading.db"

    # Your API key (keep this field name – it matches your codebase)
    polygon_api_key: str

    # REST base. Use Massive host since your docs show api.massive.com
    rest_base_url: str = "https://api.massive.com"

    class Config:
        env_file = ".env"


settings = Settings()
