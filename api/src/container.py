"""Composition root: the only place that knows which concrete classes implement the ports."""

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from core.clock import Clock, SystemClock
from core.config import Settings
from core.db import create_engine, create_session_factory, make_store_factory
from core.ids import IdGenerator, UuidGenerator
from modules.audit.service import AuditService
from modules.backtesting.application.ports import BacktestStore
from modules.backtesting.application.service import BacktestExecutor, BacktestService
from modules.backtesting.infrastructure.repository import SqlAlchemyBacktestStore
from modules.bots.application.service import BotService
from modules.market_data.application.ports import ImportStore, MarketDataSource
from modules.market_data.application.service import CandleImporter, MarketDataService
from modules.market_data.infrastructure.repository import SqlAlchemyImportStore
from modules.risk_management.application.service import KillSwitchService
from modules.strategies.domain.registry import StrategyRegistry, default_registry
from modules.trading.application.ports import TradingStore
from modules.trading.application.supervisor import BotSupervisor
from modules.trading.application.trader import BotTrader
from modules.trading.infrastructure.store import SqlAlchemyStore

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
    trading_stores: Callable[[], AbstractAsyncContextManager[TradingStore]]
    market_data: MarketDataService
    backtests: BacktestService
    bots: BotService
    kill_switch: KillSwitchService
    audit: AuditService


def build_container(settings: Settings, clock: Clock | None = None) -> Container:
    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    clock = clock or SystemClock()
    ids = UuidGenerator()
    registry = default_registry()
    import_stores = make_store_factory(session_factory, SqlAlchemyImportStore)
    backtest_stores = make_store_factory(session_factory, SqlAlchemyBacktestStore)
    trading_stores = make_store_factory(session_factory, SqlAlchemyStore)
    return Container(
        settings=settings,
        engine=engine,
        session_factory=session_factory,
        clock=clock,
        ids=ids,
        registry=registry,
        import_stores=import_stores,
        backtest_stores=backtest_stores,
        trading_stores=trading_stores,
        market_data=MarketDataService(import_stores, EXCHANGE, clock, ids),
        backtests=BacktestService(backtest_stores, registry, clock, ids),
        bots=BotService(trading_stores, registry, clock, ids),
        kill_switch=KillSwitchService(trading_stores),
        audit=AuditService(trading_stores),
    )


class JobRunner:
    """Worker-side: advances the paper-trading bots, then drains the DB-backed job queues."""

    def __init__(
        self, importer: CandleImporter, executor: BacktestExecutor, supervisor: BotSupervisor
    ) -> None:
        self._importer = importer
        self._executor = executor
        self._supervisor = supervisor

    async def recover(self) -> int:
        """Jobs left 'running' by a crashed worker are queued again (all jobs are idempotent).

        Bots need no special recovery: their state lives in the database and the supervisor
        reconciles desired vs. observed state on every pass.
        """
        return await self._importer.recover() + await self._executor.recover()

    async def run_once(self) -> bool:
        """One supervisor pass plus at most one job; False when there was no job to run."""
        await self._supervisor.run_once()
        return await self._importer.run_next() or await self._executor.run_next()


def build_job_runner(container: Container, source: MarketDataSource) -> JobRunner:
    trader = BotTrader(
        container.trading_stores, container.registry, source, container.clock, container.ids
    )
    return JobRunner(
        CandleImporter(container.import_stores, source, EXCHANGE, container.clock),
        BacktestExecutor(container.backtest_stores, container.registry, source),
        BotSupervisor(
            container.trading_stores, trader, container.registry, container.clock, container.ids
        ),
    )
