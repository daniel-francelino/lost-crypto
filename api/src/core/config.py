from enum import StrEnum
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnv(StrEnum):
    LOCAL = "local"
    TEST = "test"
    PROD = "prod"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: AppEnv = AppEnv.LOCAL
    log_level: str = "INFO"
    database_url: str = Field(
        default="postgresql+asyncpg://lostcrypto:lostcrypto@localhost:5432/lostcrypto"
    )
    # Live trading is disabled unless explicitly enabled in the worker environment.
    live_trading_enabled: bool = False
    worker_heartbeat_seconds: float = 5.0
    worker_poll_seconds: float = 2.0
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])


@lru_cache
def get_settings() -> Settings:
    return Settings()
