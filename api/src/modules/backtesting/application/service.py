import asyncio
import logging
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from decimal import Decimal
from uuid import UUID

from core.clock import Clock
from core.errors import DomainError
from core.ids import IdGenerator
from core.jobs import JobStatus
from modules.analytics.domain.metrics import compute_metrics
from modules.backtesting.application.ports import BacktestRun, BacktestStore
from modules.backtesting.domain.engine import run_backtest
from modules.backtesting.domain.models import (
    BacktestConfig,
    EquityPoint,
    hash_candles,
)
from modules.execution.domain.orders import Fill
from modules.market_data.application.ports import MarketDataSource
from modules.strategies.domain.registry import StrategyRegistry

logger = logging.getLogger(__name__)

BacktestStoreFactory = Callable[[], AbstractAsyncContextManager[BacktestStore]]

MAX_CANDLES = 200_000


class NoCandlesError(DomainError):
    """There is no stored data for the requested range; import it first."""


class TooManyCandlesError(DomainError):
    pass


class BacktestNotFound(DomainError):
    pass


class BacktestService:
    """API-side use cases: queue a run and read results."""

    def __init__(
        self,
        stores: BacktestStoreFactory,
        registry: StrategyRegistry,
        clock: Clock,
        ids: IdGenerator,
    ) -> None:
        self._stores = stores
        self._registry = registry
        self._clock = clock
        self._ids = ids

    async def create(self, config: BacktestConfig) -> BacktestRun:
        self._registry.create(config.strategy_type, config.strategy_params)  # validates
        run = BacktestRun(
            id=self._ids.new_id(),
            status=JobStatus.QUEUED,
            config=config,
            created_at=self._clock.now(),
        )
        async with self._stores() as store:
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
            await store.add_run(run)
            await store.commit()
        return run

    async def get(self, run_id: UUID) -> BacktestRun:
        async with self._stores() as store:
            run = await store.get_run(run_id)
        if run is None:
            raise BacktestNotFound(str(run_id))
        return run

    async def list_runs(self, limit: int = 50) -> list[BacktestRun]:
        async with self._stores() as store:
            return await store.list_runs(limit)

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
        self, stores: BacktestStoreFactory, registry: StrategyRegistry, source: MarketDataSource
    ) -> None:
        self._stores = stores
        self._registry = registry
        self._source = source

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
        market = await self._source.fetch_market_info(config.symbol)
        strategy = self._registry.create(config.strategy_type, config.strategy_params)

        # CPU-bound: keep the event loop (heartbeats, shutdown handling) responsive.
        outcome = await asyncio.to_thread(run_backtest, config, candles, market, strategy)
        metrics = compute_metrics(
            initial_capital=config.initial_capital,
            equity_curve=outcome.equity_curve,
            fills=outcome.fills,
            first_price=outcome.first_price,
            last_price=outcome.last_price,
            open_position=outcome.final_quantity > Decimal(0),
            rejected_signals=len(outcome.rejected),
        )
        async with self._stores() as store:
            await store.save_result(
                run.id,
                data_hash=hash_candles(candles),
                candles_count=len(candles),
                market_info=market,
                metrics=metrics.to_dict(),
                equity_curve=outcome.equity_curve,
                fills=outcome.fills,
            )
            await store.commit()
