import asyncio
import logging
import math
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from itertools import product
from typing import Any
from uuid import UUID

from core.clock import Clock
from core.errors import DomainError, NotFoundError
from core.ids import IdGenerator
from core.jobs import JobStatus
from modules.analytics.domain.metrics import compute_metrics
from modules.analytics.domain.regime import regime_report
from modules.analytics.domain.tail_risk import tail_risk
from modules.backtesting.application.ports import BacktestRun, BacktestStore, BacktestSweep
from modules.backtesting.domain import cost_ladder
from modules.backtesting.domain.break_segments import BreakRef, compute_break_segments
from modules.backtesting.domain.data_quality import (
    candle_report,
    free_parameters,
    gap_problem,
    gaps_summary,
    sample_check,
)
from modules.backtesting.domain.engine import risk_report, run_backtest
from modules.backtesting.domain.models import BacktestConfig, EquityPoint, hash_candles
from modules.backtesting.domain.periods import compute_periods
from modules.backtesting.domain.random_entries import random_entries_block
from modules.backtesting.domain.segments import compute_segments
from modules.bots.domain.models import BotConfig
from modules.exchanges.application.registry import ExchangeRegistry
from modules.execution.domain.orders import Fill
from modules.market_data.domain.models import range_coverage
from modules.strategies.domain.registry import StrategyRegistry

logger = logging.getLogger(__name__)

BacktestStoreFactory = Callable[[], AbstractAsyncContextManager[BacktestStore]]

MAX_CANDLES = 200_000
MAX_SWEEP_RUNS = 200
START_OFFSET_KEY = "start_offset_days"  # a grid key that shifts the start, not a parameter
MAX_START_OFFSETS = 25  # the book spreads the capital over 25 overlapping tranches
MAX_OFFSET_DAYS = 3650


class NoCandlesError(DomainError):
    """There is no stored data for the requested range; import it first."""


class TooManyCandlesError(DomainError):
    pass


class BacktestNotFound(NotFoundError):
    pass


class InvalidSweep(DomainError):
    pass


class DataGapsError(DomainError):
    """The range misses too many candles to run silently (book 1 ch. 3, O4)."""


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
            run.data_quality = await self._check_candles(store, config)
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
        offsets = self._start_offsets(grid)
        grid_params = {name: values for name, values in grid.items() if name != START_OFFSET_KEY}
        names = sorted(grid_params)
        if (not names and offsets is None) or any(not grid_params[n] for n in names):
            raise InvalidSweep("every grid parameter needs at least one value")
        shifts = [0] if offsets is None else offsets
        total = math.prod(len(grid_params[n]) for n in names) * len(shifts)
        if total > MAX_SWEEP_RUNS:
            raise InvalidSweep(f"a sweep may have at most {MAX_SWEEP_RUNS} combinations")

        now = self._clock.now()
        sweep_id = self._ids.new_id()
        runs: list[BacktestRun] = []
        skipped: list[dict[str, Any]] = []
        for shift, values in product(shifts, product(*(grid_params[n] for n in names))):
            params = {**base.strategy_params, **dict(zip(names, values, strict=True))}
            try:
                self._registry.create(base.strategy_type, params)
                config = replace(
                    base, start=base.start + timedelta(days=shift), strategy_params=params
                )
            except DomainError as exc:  # e.g. fast_period >= slow_period: skipped, not fatal
                skipped.append({"params": params, "reason": str(exc)})
                continue
            runs.append(
                BacktestRun(
                    id=self._ids.new_id(),
                    status=JobStatus.QUEUED,
                    config=config,
                    created_at=now,
                    sweep_id=sweep_id,
                )
            )
        if not runs:
            raise InvalidSweep("no valid parameter combination in the grid")

        sweep = BacktestSweep(sweep_id, now, base.strategy_type, grid, skipped, len(runs))
        async with self._stores() as store:
            quality = await self._check_candles(store, base)
            await store.add_sweep(sweep)  # before the runs that reference it
            for run in runs:
                run.data_quality = quality
                await store.add_run(run)
            prior = await store.count_prior_trials(sweep, base)
            await store.commit()
        return sweep, runs, prior

    @staticmethod
    def _start_offsets(grid: dict[str, list[Any]]) -> list[int] | None:
        """The start shifts (in days) of a start-sensitivity sweep, or None without them."""
        raw = grid.get(START_OFFSET_KEY)
        if raw is None:
            return None
        valid = (
            bool(raw)
            and len(raw) <= MAX_START_OFFSETS
            and all(isinstance(v, int) and not isinstance(v, bool) for v in raw)
            and all(0 <= v <= MAX_OFFSET_DAYS for v in raw)
            and len(set(raw)) == len(raw)
        )
        if not valid:
            raise InvalidSweep(
                f"{START_OFFSET_KEY} needs 1 to {MAX_START_OFFSETS} distinct whole days "
                f"between 0 and {MAX_OFFSET_DAYS}"
            )
        return list(raw)

    async def get_sweep(self, sweep_id: UUID) -> tuple[BacktestSweep, list[BacktestRun], int]:
        """The sweep, its runs, and how many earlier runs tried the same strategy and data."""
        async with self._stores() as store:
            sweep = await store.get_sweep(sweep_id)
            if sweep is None:
                raise BacktestNotFound(f"sweep {sweep_id} not found")
            runs = await store.list_sweep_runs(sweep_id)
            prior = await store.count_prior_trials(sweep, runs[0].config) if runs else 0
            return sweep, runs, prior

    async def _check_candles(self, store: BacktestStore, config: BacktestConfig) -> dict[str, Any]:
        """Refuse ranges without data, too large, or with gaps over the limits (unless
        ``allow_gaps``). Returns the gap summary stored with the run."""
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
        times = await store.candles.open_times(
            config.exchange, config.symbol, config.timeframe, config.start, config.end
        )
        coverage = range_coverage(
            times, config.timeframe, config.start, config.end, self._clock.now()
        )
        problem = gap_problem(coverage, config.timeframe)
        if problem is not None and not config.allow_gaps:
            raise DataGapsError(
                f"{problem}; import the missing candles, or set allow_gaps to run anyway"
            )
        return {"gaps": gaps_summary(coverage, config.timeframe, config.allow_gaps)}

    async def get(self, run_id: UUID) -> BacktestRun:
        async with self._stores() as store:
            run = await store.get_run(run_id)
        if run is None:
            raise BacktestNotFound(str(run_id))
        return run

    async def matching_runs(self, config: BotConfig, limit: int = 50) -> list[BacktestRun]:
        """Completed runs on the bot's market and strategy (realized-vs-backtest comparison)."""
        async with self._stores() as store:
            return await store.matching_runs(
                config.exchange, config.symbol, config.timeframe, config.strategy_type, limit
            )

    async def prior_runs(self, run: BacktestRun) -> int:
        """How many other completed runs already used this strategy on overlapping data."""
        async with self._stores() as store:
            return await store.count_prior_runs(run.id, run.config)

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
            breaks = await store.regime_breaks.inside(
                config.exchange, config.symbol, config.start, config.end
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
        free = free_parameters(
            self._registry.get(config.strategy_type).PARAMETERS, config.strategy_params
        )
        quality = {
            **(run.data_quality or {}),
            **candle_report(candles),
            "sample": sample_check(free, len(candles), metrics.round_trips),
        }
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
                data_quality=quality,
                risk_report=risk_report(outcome),
                tail_risk=tail_risk(outcome.equity_curve, candles, config.timeframe.delta),
                regime=await asyncio.to_thread(
                    regime_report, candles, outcome.equity_curve, outcome.in_market
                ),
                significance=await asyncio.to_thread(
                    random_entries_block,
                    candles,
                    outcome.fills,
                    fee_rate=config.fee_rate,
                    slippage_bps=config.slippage_bps,
                    seed=config.seed,
                ),
                break_metrics=compute_break_segments(
                    config,
                    candles,
                    outcome,
                    [BreakRef(str(b.id), b.name, b.occurred_at, b.created_at) for b in breaks],
                ),
                equity_curve=outcome.equity_curve,
                fills=outcome.fills,
            )
            await store.commit()
