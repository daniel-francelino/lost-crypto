"""Composition root: the only place that knows which concrete classes implement the ports."""

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from core.clock import Clock, SystemClock
from core.config import Settings
from core.db import create_engine, create_session_factory, make_store_factory
from core.ids import IdGenerator, UuidGenerator
from modules.backtesting.application.ports import BacktestStore
from modules.backtesting.application.service import BacktestExecutor, BacktestService
from modules.backtesting.infrastructure.repository import SqlAlchemyBacktestStore
from modules.market_data.application.ports import ImportStore, MarketDataSource
from modules.market_data.application.service import CandleImporter, MarketDataService
from modules.market_data.infrastructure.repository import SqlAlchemyImportStore
from modules.strategies.domain.registry import StrategyRegistry, default_registry

EXCHANGE = "binance"


@dataclass(slots=True)
class Container:
    settings: Settings
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]
    clock: Clock
    ids: IdGenerator
    registry: StrategyRegistry
    import_stores: Callable[[], AbstractAsyncContextManager[ImportStore]]
    backtest_stores: Callable[[], AbstractAsyncContextManager[BacktestStore]]
    market_data: MarketDataService
    backtests: BacktestService


def build_container(settings: Settings) -> Container:
    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    clock = SystemClock()
    ids = UuidGenerator()
    registry = default_registry()
    import_stores = make_store_factory(session_factory, SqlAlchemyImportStore)
    backtest_stores = make_store_factory(session_factory, SqlAlchemyBacktestStore)
    return Container(
        settings=settings,
        engine=engine,
        session_factory=session_factory,
        clock=clock,
        ids=ids,
        registry=registry,
        import_stores=import_stores,
        backtest_stores=backtest_stores,
        market_data=MarketDataService(import_stores, EXCHANGE, clock, ids),
        backtests=BacktestService(backtest_stores, registry, clock, ids),
    )


class JobRunner:
    """Worker-side: drains the DB-backed job queues (candle imports, then backtests)."""

    def __init__(self, importer: CandleImporter, executor: BacktestExecutor) -> None:
        self._importer = importer
        self._executor = executor

    async def recover(self) -> int:
        """Jobs left 'running' by a crashed worker are queued again (all jobs are idempotent)."""
        return await self._importer.recover() + await self._executor.recover()

    async def run_once(self) -> bool:
        """Run at most one job; returns False when there was nothing to do."""
        return await self._importer.run_next() or await self._executor.run_next()


def build_job_runner(container: Container, source: MarketDataSource) -> JobRunner:
    return JobRunner(
        CandleImporter(container.import_stores, source, EXCHANGE, container.clock),
        BacktestExecutor(container.backtest_stores, container.registry, source),
    )
