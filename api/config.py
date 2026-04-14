from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Local dev default: SQLite (no server needed).
    # For production with Docker set: DATABASE_URL=postgresql+asyncpg://dashboard:dashboard@db:5432/dashboard
    database_url: str = "sqlite+aiosqlite:///./dashboard.db"
    redis_url: str = "redis://localhost:6379"
    tk_api_base: str = "https://gegevensmagazijn.tweedekamer.nl/OData/v4/2.0"
    cache_ttl_tk: int = 900     # 15 min
    cache_ttl_static: int = 3600

    class Config:
        env_file = ".env"


settings = Settings()
