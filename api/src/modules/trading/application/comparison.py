"""Realized vs backtest: which backtest is the bot's equivalent, and how do the Sharpes compare
(book 2 ch. 1, O4). Read-only. The bot's metrics and the backtests come in through protocols so
this module needs neither the bots nor the backtesting application layers.
"""

from collections.abc import Callable, Sequence
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID

from core.errors import NotFoundError
from modules.analytics.domain.metrics import Metrics
from modules.backtesting.application.ports import BacktestRun
from modules.backtesting.domain.models import BacktestConfig
from modules.bots.domain.models import BotConfig
from modules.trading.application.ports import TradingStore
from modules.trading.domain.comparison import SharpeComparison, compare_sharpe

TradingStoreFactory = Callable[[], AbstractAsyncContextManager[TradingStore]]

_SECONDS_PER_DAY = Decimal(86_400)


class ComparisonNotFound(NotFoundError):
    pass


class BotPerformance(Protocol):
    async def performance(self, bot_id: UUID) -> Metrics | None: ...


class BacktestLookup(Protocol):
    async def get(self, run_id: UUID) -> BacktestRun: ...

    async def matching_runs(self, config: BotConfig, limit: int = 50) -> Sequence[BacktestRun]: ...


@dataclass(frozen=True, slots=True)
class RealizedVsBacktest:
    run_id: UUID | None
    run_created_at: datetime | None
    comparison: SharpeComparison | None
    realized_days: Decimal | None
    reason: str | None  # why there is no backtest to compare with


def _same_strategy(run_config: BacktestConfig, bot_config: BotConfig) -> bool:
    return dict(run_config.strategy_params) == dict(bot_config.strategy_params)


def pick_equivalent(runs: Sequence[BacktestRun], bot_config: BotConfig) -> BacktestRun | None:
    """Newest completed run with the bot's strategy parameters, preferring one that also used
    the bot's risk limits (a run without limits sizes all-in and is only a fallback)."""
    candidates = [r for r in runs if r.metrics is not None and _same_strategy(r.config, bot_config)]
    exact = [r for r in candidates if r.config.risk == bot_config.risk]
    pool = exact or candidates
    return max(pool, key=lambda r: r.created_at) if pool else None


def _sharpe_of(metrics: dict[str, Any] | None) -> Decimal | None:
    value = None if metrics is None else metrics.get("sharpe_ratio")
    return None if value is None else Decimal(str(value))


class ComparisonService:
    def __init__(
        self, stores: TradingStoreFactory, performance: BotPerformance, backtests: BacktestLookup
    ) -> None:
        self._stores = stores
        self._performance = performance
        self._backtests = backtests

    async def compare(self, bot_id: UUID, run_id: UUID | None = None) -> RealizedVsBacktest:
        async with self._stores() as store:
            bot = await store.bots.get(bot_id)
        if bot is None:
            raise ComparisonNotFound(f"bot {bot_id} not found")
        if run_id is not None:
            run: BacktestRun | None = await self._backtests.get(run_id)
        else:
            run = pick_equivalent(await self._backtests.matching_runs(bot.config), bot.config)
        if run is None or run.metrics is None:
            return RealizedVsBacktest(
                None, None, None, None, "no completed backtest with this bot's configuration"
            )
        realized = await self._performance.performance(bot_id)
        periods = None if realized is None else realized.return_periods
        bar_seconds = Decimal(int(bot.config.timeframe.delta.total_seconds()))
        days = None if periods is None else Decimal(periods) * bar_seconds / _SECONDS_PER_DAY
        return RealizedVsBacktest(
            run.id,
            run.created_at,
            compare_sharpe(
                None if realized is None else realized.sharpe_ratio,
                _sharpe_of(run.metrics),
                periods,
            ),
            days,
            None,
        )
