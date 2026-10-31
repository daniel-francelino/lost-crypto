from decimal import Decimal
from enum import StrEnum
from functools import lru_cache

from pydantic import Field, SecretStr
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
    # Testnet orders (fake money on the exchange sandbox) also need an explicit opt-in.
    testnet_trading_enabled: bool = False
    # HTTP API authentication: a bearer token. Optional only when APP_ENV=local.
    api_token: SecretStr | None = None
    # Fernet key(s) protecting stored exchange credentials, comma separated; the first one
    # encrypts, all of them decrypt (key rotation). Generate: python -c "from cryptography.fernet
    # import Fernet; print(Fernet.generate_key().decode())"
    credential_master_keys: SecretStr | None = None
    # Exchange integrations to enable, comma separated (see exchanges/infrastructure/catalog.py).
    enabled_exchanges: str = "binance"
    # Strategies to enable, comma separated (see strategies/catalog.py). Empty enables all.
    enabled_strategies: str = ""
    worker_heartbeat_seconds: float = 5.0
    worker_poll_seconds: float = 2.0
    worker_stale_after_seconds: float = 60.0
    # Reconciliation with the exchange (testnet/live bots).
    reconcile_interval_seconds: float = 60.0
    reconcile_absent_after_seconds: float = 30.0  # unknown order still missing after this: aborted
    native_stop_poll_seconds: float = 10.0
    # Global risk limits across all bots (operator-controlled, not editable through the API).
    risk_max_open_positions: int | None = None
    risk_max_total_exposure: Decimal | None = None
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    @property
    def master_keys(self) -> list[str]:
        raw = self.credential_master_keys.get_secret_value() if self.credential_master_keys else ""
        return [k.strip() for k in raw.split(",") if k.strip()]

    @property
    def enabled_strategy_ids(self) -> list[str]:
        return [s.strip() for s in self.enabled_strategies.split(",") if s.strip()]

    @property
    def enabled_exchange_ids(self) -> list[str]:
        return [e.strip() for e in self.enabled_exchanges.split(",") if e.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
