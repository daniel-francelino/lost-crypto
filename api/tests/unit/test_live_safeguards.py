"""Pure rules of the live-trading safeguards (end-to-end behaviour: the integration suite)."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest

from core.config import AppEnv, Settings
from factories import T0
from modules.bots.domain.models import (
    Bot,
    BotConfig,
    BotState,
    ExecutionMode,
    InvalidBotConfig,
)
from modules.exchanges.domain.connections import ApiPermissions, permission_problem
from modules.exchanges.errors import ExchangeConfigurationError
from modules.exchanges.infrastructure.binance import BinanceExchange
from modules.market_data.domain.models import Timeframe
from modules.risk_management.domain.models import LiveLimits
from modules.trading.application.supervisor import BotSupervisor

# --- API key permissions ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("permissions", "expected"),
    [
        (ApiPermissions(True, True, False, False, True), None),  # the only acceptable shape
        (ApiPermissions(True, True, True, False, True), "WITHDRAW"),
        (ApiPermissions(True, True, False, True, True), "transfer"),
        (ApiPermissions(True, False, False, False, True), "cannot trade"),
        (ApiPermissions(True, True, False, False, False), "trusted IPs"),
    ],
)
def test_only_trade_only_ip_restricted_keys_are_acceptable(
    permissions: ApiPermissions, expected: str | None
) -> None:
    problem = permission_problem(permissions, require_ip_restriction=True)
    assert (problem is None) if expected is None else (expected in (problem or ""))


def test_the_ip_restriction_requirement_can_be_relaxed_but_withdrawal_never() -> None:
    no_ip = ApiPermissions(True, True, False, False, False)
    assert permission_problem(no_ip, require_ip_restriction=False) is None
    withdraw = ApiPermissions(True, True, True, False, True)
    assert permission_problem(withdraw, require_ip_restriction=False) is not None


# --- the bot model ----------------------------------------------------------------------------


def _config(mode: ExecutionMode, connection: bool) -> BotConfig:
    return BotConfig(
        name="b",
        strategy_type="ema_crossover",
        strategy_params={},
        symbol="BTC/USDT",
        timeframe=Timeframe.H1,
        initial_capital=Decimal(1000),
        fee_rate=Decimal("0.001"),
        slippage_bps=Decimal(5),
        mode=mode,
        connection_id=uuid4() if connection else None,
    )


def test_real_exchange_modes_need_a_connection_and_paper_must_not_have_one() -> None:
    assert not ExecutionMode.PAPER.uses_exchange
    assert ExecutionMode.TESTNET.uses_exchange and ExecutionMode.LIVE.uses_exchange
    for mode in (ExecutionMode.TESTNET, ExecutionMode.LIVE):
        _config(mode, connection=True)
        with pytest.raises(InvalidBotConfig, match="needs an exchange connection"):
            _config(mode, connection=False)
    with pytest.raises(InvalidBotConfig):
        _config(ExecutionMode.PAPER, connection=True)


def test_a_live_approval_is_only_valid_for_the_version_it_was_given_to() -> None:
    bot = Bot(
        uuid4(), _config(ExecutionMode.LIVE, True), BotState.STOPPED, BotState.STOPPED, 3, T0, T0
    )
    assert not bot.has_live_approval
    bot.live_approved_config_version = 3
    assert bot.has_live_approval
    bot.config_version = 4  # any edit bumps the version...
    assert not bot.has_live_approval  # ...and silently voids the approval


# --- configuration ----------------------------------------------------------------------------


def test_live_caps_are_complete_only_when_all_three_are_set() -> None:
    assert not LiveLimits().complete
    assert not LiveLimits(Decimal(1), Decimal(2), None).complete
    assert LiveLimits(Decimal(1), Decimal(2), Decimal(3)).complete

    def settings(**kw: Any) -> Settings:
        return Settings(_env_file=None, **kw)  # type: ignore[call-arg]

    assert not settings().live_caps_configured
    assert settings(
        live_max_order_notional=1, live_max_total_exposure=2, live_max_daily_loss=3
    ).live_caps_configured


def test_live_is_off_and_demanding_by_default() -> None:
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.live_trading_enabled is False and s.testnet_trading_enabled is False
    assert s.live_min_paper_days >= 1 and s.live_require_ip_restriction is True
    assert s.live_approval_minutes <= 15  # a short-lived confirmation


# --- the adapter serves exactly one environment --------------------------------------------------


async def test_an_adapter_refuses_a_client_that_points_at_the_wrong_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import ccxt.async_support as ccxt_async

    from modules.exchanges.domain.connections import Credentials

    credentials = Credentials("k" * 20, "s" * 20)
    # sandbox requested, but the client would stay on production: must refuse, not trade there.
    monkeypatch.setattr(ccxt_async.binance, "set_sandbox_mode", lambda self, enabled: None)
    with pytest.raises(ExchangeConfigurationError, match="does not match"):
        BinanceExchange(credentials=credentials, sandbox=True)


async def test_production_and_sandbox_adapters_point_at_different_hosts() -> None:
    from modules.exchanges.domain.connections import Credentials

    credentials = Credentials("k" * 20, "s" * 20)
    live, sandbox = (
        BinanceExchange(credentials=credentials),
        BinanceExchange(credentials=credentials, sandbox=True),
    )
    try:
        assert "testnet" not in str(live._client.urls["api"])
        assert "testnet" in str(sandbox._client.urls["api"])
    finally:
        await live.aclose()
        await sandbox.aclose()


# --- worker guard evaluated on every pass ----------------------------------------------------


def _supervisor(**kwargs: Any) -> BotSupervisor:
    return BotSupervisor(None, None, None, None, None, **kwargs)  # type: ignore[arg-type]


def _live_bot(approved: bool) -> Bot:
    bot = Bot(
        uuid4(), _config(ExecutionMode.LIVE, True), BotState.RUNNING, BotState.STOPPED, 2, T0, T0
    )
    if approved:
        bot.live_approved_config_version, bot.live_approved_at = 2, datetime.now(UTC)
    return bot


@pytest.mark.parametrize(
    ("flags", "approved", "expected"),
    [
        ({}, True, "LIVE_TRADING_ENABLED"),
        ({"live_enabled": True}, True, "APP_ENV=prod"),
        ({"live_enabled": True, "is_production": True}, True, "hard caps"),
        (
            {"live_enabled": True, "is_production": True, "live_caps_configured": True},
            False,
            "approval",
        ),
        ({"live_enabled": True, "is_production": True, "live_caps_configured": True}, True, None),
    ],
)
def test_a_live_bot_runs_only_when_every_guard_is_satisfied(
    flags: dict[str, bool], approved: bool, expected: str | None
) -> None:
    problem = _supervisor(**flags)._mode_problem(_live_bot(approved))
    assert (problem is None) if expected is None else (expected in (problem or ""))


def test_testnet_and_paper_guards() -> None:
    testnet = Bot(
        uuid4(), _config(ExecutionMode.TESTNET, True), BotState.RUNNING, BotState.STOPPED, 1, T0, T0
    )
    paper = Bot(
        uuid4(), _config(ExecutionMode.PAPER, False), BotState.RUNNING, BotState.STOPPED, 1, T0, T0
    )
    assert "TESTNET_TRADING_ENABLED" in (_supervisor()._mode_problem(testnet) or "")
    assert _supervisor(testnet_enabled=True)._mode_problem(testnet) is None
    assert _supervisor()._mode_problem(paper) is None  # paper needs no permission at all
    assert AppEnv.PROD.value == "prod"
