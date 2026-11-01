"""Book 2 ch. 1 O4: realized Sharpe against the backtest's."""

from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest

from core.jobs import JobStatus
from factories import T0, make_config
from modules.analytics.domain.metrics import Metrics
from modules.backtesting.application.ports import BacktestRun
from modules.bots.domain.models import Bot, BotConfig, BotState, ExecutionMode
from modules.market_data.domain.models import Timeframe
from modules.risk_management.domain.models import RiskLimits
from modules.trading.application.comparison import (
    ComparisonNotFound,
    ComparisonService,
    pick_equivalent,
)
from modules.trading.domain.comparison import MIN_PERIODS, compare_sharpe

PARAMS = {"fast_period": 9, "slow_period": 21}


def _bot_config(risk: RiskLimits | None = None) -> BotConfig:
    return BotConfig(
        name="b",
        strategy_type="ema_crossover",
        strategy_params=dict(PARAMS),
        symbol="BTC/USDT",
        timeframe=Timeframe.H1,
        initial_capital=Decimal(1000),
        fee_rate=Decimal("0.001"),
        slippage_bps=Decimal(5),
        mode=ExecutionMode.PAPER,
        risk=risk or RiskLimits(),
    )


def _run(
    *,
    sharpe: str | None = "2",
    params: dict[str, Any] | None = None,
    age_hours: int = 0,
    **cfg: Any,
) -> BacktestRun:
    config = replace(make_config(), strategy_params=params or dict(PARAMS), **cfg)
    return BacktestRun(
        uuid4(),
        JobStatus.COMPLETED,
        config,
        T0 + timedelta(hours=age_hours),
        metrics={"sharpe_ratio": sharpe},
    )


def test_ratio_is_realized_over_backtest():
    result = compare_sharpe(Decimal("1.2"), Decimal("2.4"), 120)
    assert result.ratio == Decimal("0.5000")
    assert result.reason is None


def test_short_live_sample_gives_no_ratio_but_shows_both_numbers():
    result = compare_sharpe(Decimal("3"), Decimal("2"), MIN_PERIODS - 1)
    assert result.ratio is None
    assert "short live sample" in (result.reason or "")
    assert (result.realized, result.backtest) == (Decimal("3"), Decimal("2"))


@pytest.mark.parametrize("backtest", [Decimal(0), Decimal("-1")])
def test_a_backtest_sharpe_that_is_not_positive_has_no_ratio(backtest: Decimal):
    assert compare_sharpe(Decimal(1), backtest, 100).ratio is None


def test_missing_sharpe_on_either_side_has_no_ratio():
    assert compare_sharpe(None, Decimal(2), 100).ratio is None
    assert compare_sharpe(Decimal(1), None, 100).ratio is None


def test_equivalent_run_needs_the_same_strategy_parameters():
    other = _run(params={"fast_period": 5, "slow_period": 21})
    same = _run()
    assert pick_equivalent([other, same], _bot_config()) is same
    assert pick_equivalent([other], _bot_config()) is None


def test_equivalent_run_prefers_the_bots_risk_limits_then_the_newest():
    limits = RiskLimits(max_position_fraction=Decimal("0.5"))
    all_in_newer = _run(age_hours=5)
    sized_older = _run(age_hours=1, risk=limits)
    sized_newest = _run(age_hours=3, risk=limits)
    picked = pick_equivalent([all_in_newer, sized_older, sized_newest], _bot_config(limits))
    assert picked is sized_newest
    # No run used the bot's limits: the newest of the others is the fallback.
    assert pick_equivalent([sized_older, all_in_newer], _bot_config()) is all_in_newer


class _Stores:
    def __init__(self, bot: Bot | None) -> None:
        self.bots = self
        self._bot = bot

    async def get(self, bot_id: UUID) -> Bot | None:
        return self._bot


def _service(bot: Bot | None, runs: list[BacktestRun], realized: Metrics | None):
    stores = _Stores(bot)

    @asynccontextmanager
    async def factory():
        yield stores

    class Performance:
        async def performance(self, bot_id: UUID) -> Metrics | None:
            return realized

    class Backtests:
        async def get(self, run_id: UUID) -> BacktestRun:
            return next(r for r in runs if r.id == run_id)

        async def matching_runs(self, config: BotConfig, limit: int = 50) -> list[BacktestRun]:
            return runs

    return ComparisonService(factory, Performance(), Backtests())  # type: ignore[arg-type]


def _realized(sharpe: str, periods: int) -> Metrics:
    return Metrics(
        initial_capital=Decimal(1000),
        final_equity=Decimal(1100),
        net_pnl=Decimal(100),
        total_return_pct=Decimal(10),
        buy_and_hold_return_pct=Decimal(5),
        max_drawdown_pct=Decimal(3),
        fees_paid=Decimal(1),
        fills=4,
        round_trips=2,
        win_rate_pct=None,
        profit_factor=None,
        avg_trade_pnl=None,
        open_position=False,
        rejected_signals=0,
        sharpe_ratio=Decimal(sharpe),
        return_periods=periods,
    )


def _bot() -> Bot:
    return Bot(uuid4(), _bot_config(), BotState.RUNNING, BotState.RUNNING, 1, T0, T0)


async def test_service_compares_with_the_equivalent_backtest():
    run = _run(sharpe="2")
    result = await _service(_bot(), [run], _realized("1", 240)).compare(uuid4())
    assert result.run_id == run.id
    assert result.comparison is not None and result.comparison.ratio == Decimal("0.5000")
    assert result.realized_days == Decimal(10)  # 240 hourly returns


async def test_service_without_a_matching_backtest_explains_instead_of_failing():
    result = await _service(_bot(), [], _realized("1", 240)).compare(uuid4())
    assert result.run_id is None and result.comparison is None
    assert "no completed backtest" in (result.reason or "")


async def test_service_for_a_bot_that_never_ran_has_no_realized_sharpe():
    result = await _service(_bot(), [_run()], None).compare(uuid4())
    assert result.comparison is not None
    assert result.comparison.ratio is None and result.comparison.realized is None


async def test_service_unknown_bot_is_not_found():
    with pytest.raises(ComparisonNotFound):
        await _service(None, [], None).compare(uuid4())


async def test_service_uses_the_requested_run():
    chosen = _run(sharpe="4", params={"fast_period": 2, "slow_period": 3})
    result = await _service(_bot(), [_run(), chosen], _realized("1", 100)).compare(
        uuid4(), chosen.id
    )
    assert result.run_id == chosen.id
    assert result.comparison is not None and result.comparison.ratio == Decimal("0.2500")
