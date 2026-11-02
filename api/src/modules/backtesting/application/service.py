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
from core.errors import ConflictError, DomainError, NotFoundError
from core.ids import IdGenerator
from core.jobs import JobStatus
from modules.analytics.domain import exposure
from modules.analytics.domain.excursion import adverse_excursions
from modules.analytics.domain.metrics import compute_metrics
from modules.analytics.domain.regime import regime_report
from modules.analytics.domain.risk_ratios import periodic_returns
from modules.analytics.domain.sizing import MIN_KELLY_RETURNS, half_kelly, kelly_fraction
from modules.analytics.domain.tail_risk import tail_risk
from modules.backtesting.application.ports import BacktestRun, BacktestStore, BacktestSweep
from modules.backtesting.domain import cost_ladder
from modules.backtesting.domain.break_segments import BreakRef, compute_break_segments
from modules.backtesting.domain.data_quality import (
    candle_report,
    free_parameters,
    funding_coverage_report,
    gap_problem,
    gaps_summary,
    sample_check,
)
from modules.backtesting.domain.engine import risk_report, run_backtest
from modules.backtesting.domain.models import (
    BacktestConfig,
    BacktestOutcome,
    EquityPoint,
    InvalidBacktestConfig,
    hash_candles,
    hash_perpetual_inputs,
)
from modules.backtesting.domain.periods import compute_periods
from modules.backtesting.domain.perpetual_engine import (
    PerpetualBacktestOutcome,
    run_perpetual_backtest,
)
from modules.backtesting.domain.random_entries import random_entries_block
from modules.backtesting.domain.segments import compute_segments
from modules.bots.domain.models import BotConfig
from modules.exchanges.application.connections import ConnectionResolver
from modules.exchanges.application.registry import ExchangeRegistry
from modules.exchanges.domain.models import TradingProduct
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
        resolver: ConnectionResolver | None = None,
    ) -> None:
        self._stores = stores
        self._registry = registry
        self._exchanges = exchanges
        self._clock = clock
        self._ids = ids
        self._resolver = resolver

    async def create(self, config: BacktestConfig) -> BacktestRun:
        profile = self._exchanges.require(config.exchange, config.timeframe)
        if config.product not in profile.capabilities.products:
            raise InvalidBacktestConfig(
                f"{config.exchange} does not support {config.product.value} backtests"
            )
        if config.leverage > profile.capabilities.max_leverage:
            raise InvalidBacktestConfig(
                f"{config.exchange} supports up to {profile.capabilities.max_leverage}x leverage"
            )
        if config.product is TradingProduct.LINEAR_PERPETUAL:
            config = await self._with_tier_snapshot(config)
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
        profile = self._exchanges.require(base.exchange, base.timeframe)
        if base.product not in profile.capabilities.products:
            raise InvalidSweep(
                f"{base.exchange} does not support {base.product.value} backtest sweeps"
            )
        if base.leverage > profile.capabilities.max_leverage:
            raise InvalidSweep(
                f"{base.exchange} supports up to {profile.capabilities.max_leverage}x leverage"
            )
        if base.product is TradingProduct.LINEAR_PERPETUAL:
            base = await self._with_tier_snapshot(base)
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

    async def _with_tier_snapshot(self, config: BacktestConfig) -> BacktestConfig:
        """Pin the account-specific bracket schedule to this immutable backtest config."""
        if self._resolver is None or config.connection_id is None:
            raise InvalidBacktestConfig(
                "perpetual backtests need an active USD-M account connection to read its tiers"
            )
        exchange = await self._resolver.exchange_for(config.connection_id)
        if exchange.capabilities.exchange_id != config.exchange:
            raise InvalidBacktestConfig("connection exchange does not match backtest exchange")
        tiers = await exchange.fetch_leverage_tiers(config.symbol)
        max_notional = config.initial_capital * config.leverage
        if config.risk is not None:
            max_notional *= config.risk.max_position_fraction
            if config.risk.max_order_notional is not None:
                max_notional = min(max_notional, config.risk.max_order_notional)
        if not any(tier.supports(max_notional, config.leverage) for tier in tiers):
            raise InvalidBacktestConfig(
                f"account leverage tiers do not support {config.leverage}x "
                f"at maximum notional {max_notional}"
            )
        return replace(
            config,
            leverage_tiers=tuple(tiers),
            leverage_tiers_at=self._clock.now(),
        )

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
        report: dict[str, Any] = {
            "gaps": gaps_summary(coverage, config.timeframe, config.allow_gaps)
        }
        if config.product is TradingProduct.LINEAR_PERPETUAL:
            mark_candles = await store.perpetual_data.get_mark_candles(
                config.exchange, config.symbol, config.timeframe, config.start, config.end
            )
            if [candle.open_time for candle in mark_candles] != times:
                raise DataGapsError(
                    "perpetual backtest requires mark candles at every signal candle timestamp"
                )
            funding = await store.perpetual_data.get_funding_rates(
                config.exchange, config.symbol, config.start, config.end
            )
            if any(item.mark_price is None for item in funding):
                raise InvalidBacktestConfig(
                    "reimport funding history with event-time mark prices before running futures"
                )
            if not funding and config.end - config.start >= timedelta(hours=8):
                raise DataGapsError("perpetual funding history is missing for this range")
            report["perpetual_data"] = {
                "mark_candles": len(mark_candles),
                "funding_events": len(funding),
                "funding_first_at": funding[0].funding_time.isoformat() if funding else None,
                "funding_last_at": funding[-1].funding_time.isoformat() if funding else None,
            }
        return report

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

    async def exposure_curve(
        self, run_id: UUID, steps: int, bootstrap: bool, simulations: int, seed: int
    ) -> dict[str, Any]:
        """Growth and drawdown at exposures in (0, 1] from the run's stored equity curve (book 2
        ch. 8, O1). Raises ``ConflictError`` for a run without a finished curve and
        ``InvalidSweep``-style ``DomainError`` for a bad request."""
        run = await self.get(run_id)
        if run.status is not JobStatus.COMPLETED:
            raise ConflictError("the backtest has not finished")
        curve = await self.equity_curve(run_id)
        if len(curve) < 2:
            raise ConflictError("run the backtest again to calculate the exposure curve")
        series = periodic_returns(
            [p.time for p in curve], [p.equity for p in curve], run.config.timeframe.delta
        )
        returns = series.returns
        try:
            points = await asyncio.to_thread(
                exposure.exposure_curve,
                returns,
                steps,
                bootstrap=bootstrap,
                simulations=simulations,
                seed=seed,
            )
        except ValueError as exc:
            raise InvalidSweep(str(exc)) from exc
        mean = sum(returns, Decimal(0)) / len(returns)
        variance = sum(((r - mean) ** 2 for r in returns), Decimal(0)) / (len(returns) - 1)
        full = (
            None
            if len(returns) < MIN_KELLY_RETURNS
            else Decimal(0)
            if mean <= 0
            else kelly_fraction(mean, variance)
        )
        return {
            "points": points,
            "kelly_full": full,
            "kelly_half": None if full is None else half_kelly(full),
            "configured_fraction": run.config.risk.max_position_fraction
            if run.config.risk
            else Decimal(1),
            "ruin_fraction": exposure.ruin_fraction(returns),
            "returns": len(returns),
            "gaps": series.gaps,
            "bootstrap_returns": min(len(returns), exposure.MAX_BOOTSTRAP_RETURNS)
            if bootstrap
            else None,
        }

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
            mark_candles = (
                await store.perpetual_data.get_mark_candles(
                    config.exchange, config.symbol, config.timeframe, config.start, config.end
                )
                if config.product is TradingProduct.LINEAR_PERPETUAL
                else []
            )
            funding_rates = (
                await store.perpetual_data.get_funding_rates(
                    config.exchange, config.symbol, config.start, config.end
                )
                if config.product is TradingProduct.LINEAR_PERPETUAL
                else []
            )
        market = await self._exchanges.market_data(config.exchange).fetch_market_info(config.symbol)
        strategy = self._registry.create(config.strategy_type, config.strategy_params)

        # CPU-bound: keep the event loop (heartbeats, shutdown handling) responsive.
        outcome: BacktestOutcome | PerpetualBacktestOutcome
        if config.product is TradingProduct.LINEAR_PERPETUAL:
            outcome = await asyncio.to_thread(
                run_perpetual_backtest,
                config,
                candles,
                mark_candles,
                funding_rates,
                market,
                strategy,
                liquidation_fee_rate=config.fee_rate,
            )
            data_hash = hash_perpetual_inputs(
                candles,
                mark_candles,
                funding_rates,
                config.leverage_tiers,
                liquidation_fee_rate=config.fee_rate,
            )
        else:
            outcome = await asyncio.to_thread(run_backtest, config, candles, market, strategy)
            data_hash = hash_candles(candles)
        ladder = (
            await asyncio.to_thread(
                cost_ladder.run_cost_ladder,
                config,
                candles,
                market,
                lambda: self._registry.create(config.strategy_type, config.strategy_params),
                mark_candles,
                funding_rates,
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
        metrics_data = metrics.to_dict()
        if isinstance(outcome, PerpetualBacktestOutcome):
            metrics_data.update(
                funding_paid=str(outcome.funding_paid),
                funding_received=str(outcome.funding_received),
                liquidation_count=outcome.liquidation_count,
                liquidation_times=outcome.liquidation_times,
                maximum_notional=str(outcome.max_notional),
                minimum_liquidation_distance_pct=(
                    None
                    if outcome.min_liquidation_distance_pct is None
                    else str(outcome.min_liquidation_distance_pct)
                ),
                leverage=config.leverage,
                margin_mode=config.margin_mode.value if config.margin_mode else None,
                liquidation_fee_rate=str(config.fee_rate),
                liquidation_fee_source="configured_taker_fee_proxy",
            )
        free = free_parameters(
            self._registry.get(config.strategy_type).PARAMETERS, config.strategy_params
        )
        quality = {
            **(run.data_quality or {}),
            **candle_report(candles),
            "sample": sample_check(free, len(candles), metrics.round_trips),
        }
        if config.product is TradingProduct.LINEAR_PERPETUAL:
            quality["perpetual_data"] = {
                **(quality.get("perpetual_data") or {}),
                "mark_data_hash": hash_candles(mark_candles),
                "funding_data_hash": hash_perpetual_inputs(
                    (),
                    (),
                    funding_rates,
                    (),
                    liquidation_fee_rate=Decimal(0),
                ),
                "funding_coverage": funding_coverage_report(mark_candles, funding_rates),
                "leverage_tier_snapshot": [
                    {
                        "tier": tier.tier,
                        "min_notional": str(tier.min_notional),
                        "max_notional": str(tier.max_notional),
                        "max_leverage": tier.max_leverage,
                        "maintenance_margin_rate": str(tier.maintenance_margin_rate),
                        "cumulative_maintenance_amount": str(tier.cumulative_maintenance_amount),
                    }
                    for tier in config.leverage_tiers
                ],
                "leverage_tiers_at": (
                    config.leverage_tiers_at.isoformat()
                    if config.leverage_tiers_at is not None
                    else None
                ),
            }
        async with self._stores() as store:
            await store.save_result(
                run.id,
                data_hash=data_hash,
                candles_count=len(candles),
                market_info=market,
                metrics=metrics_data,
                segments=compute_segments(config, candles, outcome),
                periods=compute_periods(config, candles, outcome),
                cost_ladder=ladder,
                data_quality=quality,
                risk_report=risk_report(outcome),
                tail_risk=tail_risk(outcome.equity_curve, candles, config.timeframe.delta),
                regime=await asyncio.to_thread(
                    regime_report, candles, outcome.equity_curve, outcome.in_market
                ),
                significance=(
                    await asyncio.to_thread(
                        random_entries_block,
                        candles,
                        outcome.fills,
                        fee_rate=config.fee_rate,
                        slippage_bps=config.slippage_bps,
                        seed=config.seed,
                    )
                    if config.product is TradingProduct.SPOT
                    else None
                ),
                break_metrics=compute_break_segments(
                    config,
                    candles,
                    outcome,
                    [BreakRef(str(b.id), b.name, b.occurred_at, b.created_at) for b in breaks],
                ),
                excursion=(
                    await asyncio.to_thread(adverse_excursions, outcome.fills, candles)
                    if config.product is TradingProduct.SPOT
                    else None
                ),
                equity_curve=outcome.equity_curve,
                fills=outcome.fills,
            )
            await store.commit()
