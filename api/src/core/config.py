from decimal import Decimal
from enum import StrEnum
from functools import lru_cache

from pydantic import Field, SecretStr, field_validator
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
    # --- Live trading (REAL MONEY). Off unless every one of these is deliberately set. ----
    # Hard caps independent of any bot's own limits; all three are required for a live bot to run.
    live_max_order_notional: Decimal | None = None  # quote currency, per order
    live_max_total_exposure: Decimal | None = None  # quote currency, all live positions
    live_max_daily_loss: Decimal | None = None  # quote currency, per bot per UTC day
    live_min_paper_days: int = 7  # paper history required before a bot may be approved for live
    live_require_ip_restriction: bool = True  # refuse live keys that work from any IP
    live_approval_minutes: int = 10  # lifetime of a live confirmation token
    # HTTP API authentication: a bearer token. Optional only when APP_ENV=local.
    api_token: SecretStr | None = None
    # User login (frontend): secret signing the short-lived access tokens (>= 32 chars). Enables
    # /auth/login. Generate: python -c "import secrets; print(secrets.token_urlsafe(48))"
    jwt_secret: SecretStr | None = None
    access_token_minutes: int = 15
    refresh_token_days: float = 7
    login_max_failures: int = 5  # consecutive wrong passwords before the account locks
    login_lockout_minutes: int = 15
    refresh_reuse_grace_seconds: int = 10  # tolerated gap for a double-fired refresh request
    cookie_secure: bool | None = None  # None: secure cookies everywhere except APP_ENV=local
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

    @field_validator(
        "api_token",
        "credential_master_keys",
        "jwt_secret",
        "live_max_order_notional",
        "live_max_total_exposure",
        "live_max_daily_loss",
        "risk_max_open_positions",
        "risk_max_total_exposure",
        mode="before",
    )
    @classmethod
    def _empty_means_unset(cls, value: object) -> object:
        return None if isinstance(value, str) and not value.strip() else value

    @property
    def live_caps_configured(self) -> bool:
        return None not in (
            self.live_max_order_notional,
            self.live_max_total_exposure,
            self.live_max_daily_loss,
        )

    @property
    def auth_enabled(self) -> bool:
        return self.api_token is not None or self.jwt_secret is not None

    @property
    def secure_cookies(self) -> bool:
        return (
            self.cookie_secure
            if self.cookie_secure is not None
            else self.app_env is not AppEnv.LOCAL
        )

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
