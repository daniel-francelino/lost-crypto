from decimal import Decimal
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from core.config import AppEnv, Settings
from core.security.auth import InsecureConfiguration, assert_secure_configuration
from core.security.vault import CredentialVault, VaultError, VaultNotConfigured
from factories import T0
from main import create_app
from modules.execution.domain.orders import Fill
from modules.portfolio.domain.models import InsufficientFunds, PortfolioState
from modules.strategies.domain.types import Side

# --- vault ----------------------------------------------------------------------------------


def test_vault_round_trips_and_ciphertext_hides_the_plaintext() -> None:
    vault = CredentialVault([Fernet.generate_key().decode()])
    sealed = vault.seal("my-secret-api-key")
    assert b"my-secret-api-key" not in sealed
    assert vault.open(sealed) == "my-secret-api-key"
    assert vault.seal("x") != vault.seal("x")  # random IV: equal secrets do not look equal


def test_vault_refuses_a_wrong_key_and_tampered_data() -> None:
    sealed = CredentialVault([Fernet.generate_key().decode()]).seal("secret")
    with pytest.raises(VaultError):
        CredentialVault([Fernet.generate_key().decode()]).open(sealed)
    key = Fernet.generate_key().decode()
    good = CredentialVault([key]).seal("secret")
    with pytest.raises(VaultError):
        CredentialVault([key]).open(good[:-4] + b"AAAA")


def test_master_key_rotation_keeps_old_records_readable() -> None:
    old, new = Fernet.generate_key().decode(), Fernet.generate_key().decode()
    sealed_with_old = CredentialVault([old]).seal("secret")
    rotating = CredentialVault([new, old])  # first encrypts, all decrypt
    assert rotating.open(sealed_with_old) == "secret"
    migrated = rotating.rotate(sealed_with_old)
    assert CredentialVault([new]).open(migrated) == "secret"
    assert rotating.key_id != CredentialVault([old]).key_id


def test_vault_needs_valid_keys() -> None:
    with pytest.raises(VaultNotConfigured):
        CredentialVault([])
    with pytest.raises(VaultNotConfigured):
        CredentialVault(["not-a-fernet-key"])


def test_master_keys_setting_is_comma_separated_and_secret() -> None:
    settings = Settings(_env_file=None, credential_master_keys="a, b ,")  # type: ignore[call-arg]
    assert settings.master_keys == ["a", "b"]
    assert "a, b" not in repr(settings)  # SecretStr: not leaked by repr
    assert Settings(_env_file=None).master_keys == []  # type: ignore[call-arg]


# --- API token ------------------------------------------------------------------------------


def test_production_refuses_to_start_without_an_api_token() -> None:
    with pytest.raises(InsecureConfiguration):
        assert_secure_configuration(Settings(_env_file=None, app_env=AppEnv.PROD))  # type: ignore[call-arg]
    assert_secure_configuration(Settings(_env_file=None, app_env=AppEnv.PROD, api_token="t"))  # type: ignore[call-arg]
    assert_secure_configuration(Settings(_env_file=None))  # type: ignore[call-arg]  # local: ok


def _client(**overrides: object) -> TestClient:
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        database_url="postgresql+asyncpg://x:x@127.0.0.1:1/x",
        **overrides,
    )
    return TestClient(create_app(settings))


def test_business_endpoints_require_the_token_but_health_stays_open() -> None:
    with _client(api_token="s3cret-token") as client:
        assert client.get("/api/v1/health/live").status_code == 200
        assert client.get("/api/v1/strategies").status_code == 401
        wrong = {"Authorization": "Bearer nope"}
        assert client.get("/api/v1/strategies", headers=wrong).status_code == 401
        assert (
            client.get(
                "/api/v1/strategies", headers={"Authorization": "Basic s3cret-token"}
            ).status_code
            == 401
        )
        right = {"Authorization": "Bearer s3cret-token"}
        assert client.get("/api/v1/strategies", headers=right).status_code == 200


def test_endpoints_are_open_on_a_local_machine_without_a_token() -> None:
    with _client() as client:
        assert client.get("/api/v1/strategies").status_code == 200


def test_credential_endpoints_refuse_to_work_without_a_token() -> None:
    body = {"label": "x", "api_key": "k" * 12, "api_secret": "s" * 12}
    with _client() as client:  # local, no token: normal endpoints open, secrets endpoints shut
        response = client.post("/api/v1/exchange-connections", json=body)
        assert response.status_code == 403 and "API_TOKEN" in response.json()["detail"]


def test_live_connections_are_refused_outside_production_and_without_confirmation() -> None:
    key = Fernet.generate_key().decode()
    body = {"label": "x", "environment": "live", "api_key": "k" * 12, "api_secret": "s" * 12}
    headers = {"Authorization": "Bearer t"}
    with _client(api_token="t", credential_master_keys=key) as local:  # APP_ENV=local
        response = local.post("/api/v1/exchange-connections", json=body, headers=headers)
        assert response.status_code == 422 and "APP_ENV=prod" in response.json()["detail"]
    with _client(api_token="t", credential_master_keys=key, app_env=AppEnv.PROD) as prod:
        response = prod.post("/api/v1/exchange-connections", json=body, headers=headers)
        assert response.status_code == 422 and "confirm_real_money" in response.json()["detail"]


def test_connection_endpoints_report_a_missing_vault_as_unavailable() -> None:
    body = {"label": "x", "api_key": "k" * 12, "api_secret": "s" * 12}
    with _client(api_token="t") as client:  # token set, but no CREDENTIAL_MASTER_KEYS
        response = client.post(
            "/api/v1/exchange-connections", json=body, headers={"Authorization": "Bearer t"}
        )
        assert response.status_code == 503 and "CREDENTIAL_MASTER_KEYS" in response.json()["detail"]


# --- portfolio accounting for real exchanges ------------------------------------------------


def _buy(qty: str, price: str, fee: str = "0", fee_base: str = "0") -> Fill:
    return Fill(T0, Side.BUY, Decimal(qty), Decimal(price), Decimal(fee), Decimal(fee_base), "T1")


def test_a_fee_paid_in_the_base_asset_reduces_what_is_received() -> None:
    p = PortfolioState.new(uuid4(), Decimal(1000))
    p.apply_fill(_buy("1", "100", fee_base="0.001"))  # buy 1 BTC, 0.001 BTC fee
    assert p.quantity == Decimal("0.999")  # what the exchange account actually holds
    assert p.cash == Decimal(900)  # no quote fee
    assert p.avg_entry_price == Decimal("100.1") / Decimal("0.999")  # fee value is in the basis
    assert p.fees_paid == Decimal("0.1")  # 0.001 BTC valued at 100


def test_selling_after_a_base_fee_buy_realises_the_right_pnl() -> None:
    p = PortfolioState.new(uuid4(), Decimal(1000))
    p.apply_fill(_buy("1", "100", fee_base="0.001"))
    sell = Fill(T0, Side.SELL, Decimal("0.999"), Decimal(110), Decimal("0.10989"), Decimal(0), "T2")
    p.apply_fill(sell)
    assert p.quantity == 0
    proceeds = Decimal("0.999") * 110 - Decimal("0.10989")
    assert abs(p.realized_pnl - (proceeds - Decimal("100.1"))) < Decimal("1e-20")


def test_reservations_prevent_spending_the_same_money_twice() -> None:
    p = PortfolioState.new(uuid4(), Decimal(1000))
    p.reserve(cash=Decimal(600))
    assert p.available_cash == Decimal(400) and p.cash == Decimal(1000)  # equity unaffected
    assert p.equity(Decimal(1)) == Decimal(1000)
    with pytest.raises(InsufficientFunds):
        p.reserve(cash=Decimal(500))
    p.release(cash=Decimal(600))
    assert p.available_cash == Decimal(1000)
    p.release(cash=Decimal(5))  # over-release is clamped, never negative
    assert p.reserved_cash == 0


def test_empty_numeric_settings_from_docker_compose_count_as_unset() -> None:
    settings = Settings(  # type: ignore[call-arg]
        _env_file=None,
        live_max_order_notional="",
        live_max_total_exposure="",
        live_max_daily_loss="",
        risk_max_open_positions="",
        risk_max_total_exposure="  ",
    )
    assert settings.live_max_order_notional is None and not settings.live_caps_configured
    assert settings.risk_max_open_positions is None and settings.risk_max_total_exposure is None
