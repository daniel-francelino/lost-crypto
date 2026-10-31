import asyncio
import logging
import math
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import replace
from decimal import Decimal
from itertools import product
from typing import Any
from uuid import UUID

from core.clock import Clock
from core.errors import DomainError, NotFoundError
from core.ids import IdGenerator
from core.jobs import JobStatus
from modules.analytics.domain.metrics import compute_metrics
from modules.backtesting.application.ports import BacktestRun, BacktestStore, BacktestSweep
from modules.backtesting.domain import cost_ladder
from modules.backtesting.domain.engine import run_backtest
from modules.backtesting.domain.models import BacktestConfig, EquityPoint, hash_candles
from modules.backtesting.domain.periods import compute_periods
from modules.backtesting.domain.segments import compute_segments
from modules.exchanges.application.registry import ExchangeRegistry
from modules.execution.domain.orders import Fill
from modules.strategies.domain.registry import StrategyRegistry

logger = logging.getLogger(__name__)

BacktestStoreFactory = Callable[[], AbstractAsyncContextManager[BacktestStore]]

MAX_CANDLES = 200_000
MAX_SWEEP_RUNS = 200


class NoCandlesError(DomainError):
    """There is no stored data for the requested range; import it first."""


class TooManyCandlesError(DomainError):
    pass


class BacktestNotFound(NotFoundError):
    pass


class InvalidSweep(DomainError):
    pass


class BacktestService:
    """API-side use cases: queue a run and read results."""

    def __init__(
        self,
        stores: BacktestStoreFactory,
        registry: StrategyRegistry,
        exchanges: ExchangeRegistry,
        clock: Clock,
        ids: IdGenerator,
    ) -> None:
        self._stores = stores
        self._registry = registry
        self._exchanges = exchanges
        self._clock = clock
        self._ids = ids

    async def create(self, config: BacktestConfig) -> BacktestRun:
        self._exchanges.require(config.exchange, config.timeframe)
        self._registry.create(config.strategy_type, config.strategy_params)  # validates
        run = BacktestRun(
            id=self._ids.new_id(),
            status=JobStatus.QUEUED,
            config=config,
            created_at=self._clock.now(),
        )
        async with self._stores() as store:
            await self._check_candles(store, config)
            await store.add_run(run)
            await store.commit()
        return run

    async def create_sweep(
        self, base: BacktestConfig, grid: dict[str, list[Any]]
    ) -> tuple[BacktestSweep, list[BacktestRun], int]:
        """Queue one run per parameter combination of ``grid`` (over the same data).

        Also returns the number of earlier runs on the same strategy and data (prior trials).
        """
        self._exchanges.require(base.exchange, base.timeframe)
        if base.cost_sensitivity:
            raise InvalidSweep("cost sensitivity is per backtest; open the chosen run instead")
        names = sorted(grid)
        if not names or any(not grid[n] for n in names):
            raise InvalidSweep("every grid parameter needs at least one value")
        if math.prod(len(grid[n]) for n in names) > MAX_SWEEP_RUNS:
            raise InvalidSweep(f"a sweep may have at most {MAX_SWEEP_RUNS} combinations")

        now = self._clock.now()
        sweep_id = self._ids.new_id()
        runs: list[BacktestRun] = []
        skipped: list[dict[str, Any]] = []
        for values in product(*(grid[n] for n in names)):
            params = {**base.strategy_params, **dict(zip(names, values, strict=True))}
            try:
                self._registry.create(base.strategy_type, params)
            except DomainError as exc:  # e.g. fast_period >= slow_period: skipped, not fatal
                skipped.append({"params": params, "reason": str(exc)})
                continue
            runs.append(
                BacktestRun(
                    id=self._ids.new_id(),
                    status=JobStatus.QUEUED,
                    config=replace(base, strategy_params=params),
                    created_at=now,
                    sweep_id=sweep_id,
                )
            )
        if not runs:
            raise InvalidSweep("no valid parameter combination in the grid")

        sweep = BacktestSweep(sweep_id, now, base.strategy_type, grid, skipped, len(runs))
        async with self._stores() as store:
            await self._check_candles(store, base)
            await store.add_sweep(sweep)  # before the runs that reference it
            for run in runs:
                await store.add_run(run)
            prior = await store.count_prior_trials(sweep, base)
            await store.commit()
        return sweep, runs, prior

    async def get_sweep(self, sweep_id: UUID) -> tuple[BacktestSweep, list[BacktestRun], int]:
        """The sweep, its runs, and how many earlier runs tried the same strategy and data."""
        async with self._stores() as store:
            sweep = await store.get_sweep(sweep_id)
            if sweep is None:
                raise BacktestNotFound(f"sweep {sweep_id} not found")
            runs = await store.list_sweep_runs(sweep_id)
            prior = await store.count_prior_trials(sweep, runs[0].config) if runs else 0
            return sweep, runs, prior

    @staticmethod
    async def _check_candles(store: BacktestStore, config: BacktestConfig) -> None:
        available = await store.candles.count_range(
            config.exchange, config.symbol, config.timeframe, config.start, config.end
        )
        if available == 0:
            raise NoCandlesError(
                f"no {config.symbol} {config.timeframe} candles stored between "
                f"{config.start.isoformat()} and {config.end.isoformat()}; import them first"
            )
        if available > MAX_CANDLES:
            raise TooManyCandlesError(f"{available} candles exceed the limit of {MAX_CANDLES}")
        if config.cost_sensitivity and available > cost_ladder.MAX_CANDLES:
            raise TooManyCandlesError(
                f"cost sensitivity re-runs the backtest per cost level; {available} candles "
                f"exceed its limit of {cost_ladder.MAX_CANDLES}"
            )

    async def get(self, run_id: UUID) -> BacktestRun:
        async with self._stores() as store:
            run = await store.get_run(run_id)
        if run is None:
            raise BacktestNotFound(str(run_id))
        return run

    async def list_runs(self, limit: int = 50, offset: int = 0) -> tuple[list[BacktestRun], int]:
        async with self._stores() as store:
            return await store.list_runs(limit, offset), await store.count_runs()

    async def trades(self, run_id: UUID) -> list[Fill]:
        await self.get(run_id)
        async with self._stores() as store:
            return await store.list_trades(run_id)

    async def equity_curve(self, run_id: UUID) -> list[EquityPoint]:
        async with self._stores() as store:
            curve = await store.get_equity_curve(run_id)
        if curve is None:
            await self.get(run_id)  # raises BacktestNotFound for unknown ids
            return []
        return curve


class BacktestExecutor:
    """Worker-side: claims queued runs, executes them and persists the results."""

    def __init__(
        self, stores: BacktestStoreFactory, registry: StrategyRegistry, exchanges: ExchangeRegistry
    ) -> None:
        self._stores = stores
        self._registry = registry
        self._exchanges = exchanges

    async def recover(self) -> int:
        async with self._stores() as store:
            count = await store.requeue_running()
            await store.commit()
        return count

    async def run_next(self) -> bool:
        async with self._stores() as store:
            run = await store.claim_next_queued()
            await store.commit()
        if run is None:
            return False
        logger.info("backtest %s started", run.id)
        try:
            await self._execute(run)
        except Exception as exc:
            logger.exception("backtest %s failed", run.id)
            async with self._stores() as store:
                await store.mark_failed(run.id, f"{type(exc).__name__}: {exc}"[:500])
                await store.commit()
        else:
            logger.info("backtest %s completed", run.id)
        return True

    async def _execute(self, run: BacktestRun) -> None:
        config = run.config
        async with self._stores() as store:
            candles = await store.candles.get_range(
                config.exchange, config.symbol, config.timeframe, config.start, config.end
            )
        market = await self._exchanges.market_data(config.exchange).fetch_market_info(config.symbol)
        strategy = self._registry.create(config.strategy_type, config.strategy_params)

        # CPU-bound: keep the event loop (heartbeats, shutdown handling) responsive.
        outcome = await asyncio.to_thread(run_backtest, config, candles, market, strategy)
        ladder = (
            await asyncio.to_thread(
                cost_ladder.run_cost_ladder,
                config,
                candles,
                market,
                lambda: self._registry.create(config.strategy_type, config.strategy_params),
            )
            if config.cost_sensitivity
            else None
        )
        metrics = compute_metrics(
            initial_capital=config.initial_capital,
            equity_curve=outcome.equity_curve,
            fills=outcome.fills,
            first_price=outcome.first_price,
            last_price=outcome.last_price,
            open_position=outcome.final_quantity > Decimal(0),
            rejected_signals=len(outcome.rejected),
            bar=config.timeframe.delta,
            benchmark_prices=[c.close for c in candles],
            in_market=outcome.in_market,
        )
        async with self._stores() as store:
            await store.save_result(
                run.id,
                data_hash=hash_candles(candles),
                candles_count=len(candles),
                market_info=market,
                metrics=metrics.to_dict(),
                segments=compute_segments(config, candles, outcome),
                periods=compute_periods(config, candles, outcome),
                cost_ladder=ladder,
                equity_curve=outcome.equity_curve,
                fills=outcome.fills,
            )
            await store.commit()
