"""Composition root: the only place that knows which concrete classes implement the ports."""

import logging
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from core.clock import Clock, SystemClock
from core.config import AppEnv, Settings
from core.db import create_engine, create_session_factory, make_store_factory
from core.ids import IdGenerator, UuidGenerator
from core.security.passwords import PasswordService
from core.security.tokens import TokenCodec
from core.security.vault import CredentialVault
from modules.audit.service import AuditService
from modules.auth.service import AuthConfig, AuthService
from modules.backtesting.application.ports import BacktestStore
from modules.backtesting.application.service import BacktestExecutor, BacktestService
from modules.backtesting.infrastructure.repository import SqlAlchemyBacktestStore
from modules.bots.application.live import LiveService
from modules.bots.application.service import BotService
from modules.bots.domain.models import BotState
from modules.exchanges.application.connections import ConnectionResolver, ConnectionService
from modules.exchanges.application.registry import ExchangeRegistry
from modules.exchanges.infrastructure.catalog import build_exchange_registry
from modules.market_data.application.listings import ListingRecorder
from modules.market_data.application.ports import ImportStore
from modules.market_data.application.service import CandleImporter, MarketDataService
from modules.market_data.application.updater import (
    CandleUpdater,
    FollowedSeries,
    Series,
    UpdaterConfig,
    UpdateReport,
)
from modules.market_data.infrastructure.repository import SqlAlchemyImportStore
from modules.notifications.application.evaluator import AlertEvaluator
from modules.notifications.application.service import AlertMonitor, AlertService, MonitorStore
from modules.risk_management.application.service import KillSwitchService
from modules.risk_management.domain.models import GlobalRiskLimits, LiveLimits
from modules.strategies.catalog import build_strategy_registry
from modules.strategies.domain.registry import StrategyRegistry
from modules.trading.application.comparison import ComparisonService
from modules.trading.application.operations import OperationsMonitor
from modules.trading.application.orders import OrderExecutor
from modules.trading.application.parity import ParityExecutor, ParityService
from modules.trading.application.ports import TradingStore
from modules.trading.application.reconciler import Reconciler
from modules.trading.application.status import StatusService
from modules.trading.application.supervisor import BotSupervisor
from modules.trading.application.trader import BotTrader
from modules.trading.infrastructure.store import SqlAlchemyStore

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class Container:
    settings: Settings
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]
    clock: Clock
    ids: IdGenerator
    registry: StrategyRegistry
    exchanges: ExchangeRegistry
    import_stores: Callable[[], AbstractAsyncContextManager[ImportStore]]
    backtest_stores: Callable[[], AbstractAsyncContextManager[BacktestStore]]
    trading_stores: Callable[[], AbstractAsyncContextManager[TradingStore]]
    alert_stores: Callable[[], AbstractAsyncContextManager[MonitorStore]]
    market_data: MarketDataService
    backtests: BacktestService
    bots: BotService
    kill_switch: KillSwitchService
    audit: AuditService
    alerts: AlertService
    alert_monitor: AlertMonitor
    status: StatusService
    parity: ParityService
    comparison: ComparisonService
    connections: ConnectionService
    resolver: ConnectionResolver
    auth: AuthService


def build_container(
    settings: Settings,
    clock: Clock | None = None,
    exchanges: ExchangeRegistry | None = None,
) -> Container:
    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    clock = clock or SystemClock()
    ids = UuidGenerator()
    registry = build_strategy_registry(settings.enabled_strategy_ids)
    exchanges = exchanges or build_exchange_registry(settings.enabled_exchange_ids)
    import_stores = make_store_factory(session_factory, SqlAlchemyImportStore)
    backtest_stores = make_store_factory(session_factory, SqlAlchemyBacktestStore)
    trading_stores = make_store_factory(session_factory, SqlAlchemyStore)
    alert_stores = make_store_factory(session_factory, SqlAlchemyStore)
    live = LiveService(trading_stores, settings, clock, ids)
    keys = settings.master_keys
    vault = CredentialVault(keys) if keys else None  # None: connections are unavailable
    status = StatusService(
        trading_stores,
        clock,
        exchanges.exchange_ids,
        timedelta(seconds=settings.worker_stale_after_seconds),
    )
    backtests = BacktestService(backtest_stores, registry, exchanges, clock, ids)
    bots = BotService(trading_stores, registry, exchanges, clock, ids, live)
    return Container(
        settings=settings,
        engine=engine,
        session_factory=session_factory,
        clock=clock,
        ids=ids,
        registry=registry,
        exchanges=exchanges,
        import_stores=import_stores,
        backtest_stores=backtest_stores,
        trading_stores=trading_stores,
        alert_stores=alert_stores,
        market_data=MarketDataService(import_stores, exchanges, clock, ids),
        backtests=backtests,
        bots=bots,
        kill_switch=KillSwitchService(trading_stores),
        audit=AuditService(trading_stores),
        alerts=AlertService(alert_stores, clock),
        alert_monitor=build_alert_monitor(settings, alert_stores, status, clock),
        auth=AuthService(
            trading_stores,
            PasswordService(),
            TokenCodec(
                settings.jwt_secret.get_secret_value(),
                timedelta(minutes=settings.access_token_minutes),
            )
            if settings.jwt_secret
            else None,
            clock,
            ids,
            AuthConfig(
                refresh_ttl=timedelta(days=settings.refresh_token_days),
                max_failed_logins=settings.login_max_failures,
                lockout=timedelta(minutes=settings.login_lockout_minutes),
                reuse_grace=timedelta(seconds=settings.refresh_reuse_grace_seconds),
            ),
        ),
        connections=ConnectionService(
            trading_stores,
            vault,
            exchanges,
            clock,
            ids,
            live_allowed=settings.app_env is AppEnv.PROD,
        ),
        resolver=ConnectionResolver(trading_stores, vault, exchanges, clock),
        parity=ParityService(trading_stores, clock, ids),
        comparison=ComparisonService(trading_stores, bots, backtests),
        status=status,
    )


class JobRunner:
    """Worker-side: advances the paper-trading bots, keeps candles current, watches for
    failures, then drains the DB-backed job queues."""

    def __init__(
        self,
        importer: CandleImporter,
        executor: BacktestExecutor,
        supervisor: BotSupervisor,
        listings: ListingRecorder | None = None,
        operations: OperationsMonitor | None = None,
        parity: ParityExecutor | None = None,
        updater: CandleUpdater | None = None,
        alert_monitor: AlertMonitor | None = None,
    ) -> None:
        self._importer = importer
        self._executor = executor
        self._supervisor = supervisor
        self._listings = listings
        self._operations = operations
        self._parity = parity
        self._updater = updater
        self._alert_monitor = alert_monitor

    async def recover(self) -> int:
        """Jobs left 'running' by a crashed worker are queued again (all jobs are idempotent).

        Bots need no special recovery: their state lives in the database and the supervisor
        reconciles desired vs. observed state on every pass.
        """
        return await self._importer.recover() + await self._executor.recover()

    async def run_once(self) -> bool:
        """One supervisor pass, the candle update and alert checks (each throttled by its own
        interval and never fatal), plus at most one job; False when there was no job to run."""
        if self._operations is not None:
            await self._operations.run_due()  # clock skew (once a minute), before trading on it
        await self._supervisor.run_once()
        if self._listings is not None:
            await self._listings.run_due()  # once a day; failures are logged, never raised
        if self._updater is not None:
            try:
                await self._updater.run_if_due()
            except Exception:
                logger.exception("candle update failed")
        if self._alert_monitor is not None:
            await self._alert_monitor.run_worker_if_due()
        return (
            await self._importer.run_next()
            or await self._executor.run_next()
            or (self._parity is not None and await self._parity.run_next())
        )


def build_alert_monitor(
    settings: Settings,
    stores: Callable[[], AbstractAsyncContextManager[MonitorStore]],
    status: StatusService,
    clock: Clock,
    update_report: Callable[[], UpdateReport] | None = None,
) -> AlertMonitor:
    return AlertMonitor(
        stores,
        status,
        AlertEvaluator(stores, clock, timedelta(seconds=settings.alert_cooldown_seconds)),
        clock,
        timedelta(seconds=settings.alert_evaluation_seconds),
        timedelta(days=settings.alert_retention_days),
        update_report,
    )


def build_candle_updater(container: Container) -> CandleUpdater:
    settings = container.settings

    def followed() -> FollowedSeries:
        async def series() -> set[Series]:
            async with container.trading_stores() as store:
                bots = await store.bots.list_active()
            return {
                Series(b.config.exchange, b.config.symbol, b.config.timeframe)
                for b in bots
                if b.desired_state is not BotState.STOPPED
            }

        return series

    return CandleUpdater(
        container.import_stores,
        container.exchanges,
        container.clock,
        followed(),
        UpdaterConfig(
            interval=timedelta(seconds=settings.candle_update_interval_seconds),
            grace=timedelta(seconds=settings.candle_update_grace_seconds),
            discover_every=timedelta(seconds=settings.candle_update_discover_seconds),
            max_age=timedelta(days=settings.candle_update_max_age_days),
            stale_after_candles=settings.candle_stale_after_candles,
        ),
    )


def build_job_runner(container: Container) -> JobRunner:
    settings = container.settings
    live_limits = LiveLimits(
        max_order_notional=settings.live_max_order_notional,
        max_total_exposure=settings.live_max_total_exposure,
        max_daily_loss=settings.live_max_daily_loss,
    )
    executor = OrderExecutor(
        container.trading_stores,
        container.resolver,
        container.clock,
        container.ids,
        timedelta(seconds=settings.reconcile_absent_after_seconds),
        live_limits,
    )
    reconciler = Reconciler(container.trading_stores, container.resolver, executor, container.clock)
    trader = BotTrader(
        container.trading_stores,
        container.registry,
        container.exchanges,
        container.clock,
        container.ids,
        GlobalRiskLimits(
            max_open_positions=settings.risk_max_open_positions,
            max_total_exposure=settings.risk_max_total_exposure,
        ),
        executor,
        live_limits,
    )
    updater = build_candle_updater(container) if settings.candle_update_enabled else None
    return JobRunner(
        CandleImporter(container.import_stores, container.exchanges, container.clock),
        BacktestExecutor(container.backtest_stores, container.registry, container.exchanges),
        BotSupervisor(
            container.trading_stores,
            trader,
            container.registry,
            container.clock,
            container.ids,
            resolver=container.resolver,
            executor=executor,
            reconciler=reconciler,
            testnet_enabled=settings.testnet_trading_enabled,
            live_enabled=settings.live_trading_enabled,
            is_production=settings.app_env is AppEnv.PROD,
            live_caps_configured=live_limits.complete,
            live_require_ip_restriction=settings.live_require_ip_restriction,
            reconcile_interval=timedelta(seconds=settings.reconcile_interval_seconds),
            stop_poll_interval=timedelta(seconds=settings.native_stop_poll_seconds),
        ),
        ListingRecorder(container.import_stores, container.exchanges, container.clock),
        OperationsMonitor(container.trading_stores, container.exchanges, container.clock),
        ParityExecutor(
            container.trading_stores, container.registry, container.exchanges, container.clock
        ),
        updater,
        build_alert_monitor(
            settings,
            container.alert_stores,
            container.status,
            container.clock,
            updater.report if updater is not None else None,
        ),
    )
