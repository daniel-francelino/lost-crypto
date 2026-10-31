"""Reconciles each bot's ``desired_state`` (set by the API) with what the worker is doing."""

import logging
from datetime import datetime, timedelta
from uuid import UUID

from core.clock import Clock
from core.ids import IdGenerator
from core.security.vault import VaultError, VaultNotConfigured
from modules.audit.models import AuditEvent
from modules.bots.domain.models import Bot, BotState, ExecutionMode
from modules.exchanges.application.connections import ConnectionResolver, InvalidConnection
from modules.exchanges.errors import AuthenticationFailed
from modules.risk_management.domain.models import KillSwitchState
from modules.strategies.domain.registry import StrategyRegistry
from modules.trading.application.orders import OrderExecutor
from modules.trading.application.reconciler import Reconciler
from modules.trading.application.trader import BotTrader, TradingStoreFactory
from modules.trading.domain.models import MAX_CONSECUTIVE_FAILURES, SessionStatus, TradingSession

logger = logging.getLogger(__name__)

_MAX_BACKOFF_SECONDS = 60
# Retrying cannot fix these: stop the bot and let the operator look.
_FATAL = (AuthenticationFailed, InvalidConnection, VaultError, VaultNotConfigured)


class BotSupervisor:
    """One pass per call: failures are isolated per bot so one bad bot never stops the others.

    Transient failures back off exponentially; after ``MAX_CONSECUTIVE_FAILURES`` the bot is
    put in the ``error`` state and paused instead of retrying forever.
    """

    def __init__(
        self,
        stores: TradingStoreFactory,
        trader: BotTrader,
        registry: StrategyRegistry,
        clock: Clock,
        ids: IdGenerator,
        *,
        resolver: ConnectionResolver | None = None,
        executor: OrderExecutor | None = None,
        reconciler: Reconciler | None = None,
        testnet_enabled: bool = False,
        reconcile_interval: timedelta = timedelta(seconds=60),
        stop_poll_interval: timedelta = timedelta(seconds=10),
    ) -> None:
        self._stores = stores
        self._trader = trader
        self._registry = registry
        self._clock = clock
        self._ids = ids
        self._failures: dict[UUID, int] = {}
        self._retry_at: dict[UUID, datetime] = {}
        self._resolver = resolver
        self._executor = executor
        self._reconciler = reconciler
        self._testnet_enabled = testnet_enabled
        self._reconcile_interval = reconcile_interval
        self._stop_poll_interval = stop_poll_interval
        self._last_reconcile: datetime | None = None
        self._last_stop_poll: datetime | None = None

    async def run_once(self) -> None:
        async with self._stores() as store:
            kill_switch = await store.flags.get_kill_switch()
            bots = await store.bots.list_active()
        if kill_switch.active:
            bots = await self._apply_kill_switch(bots, kill_switch)

        await self._housekeeping(bots)

        running: list[UUID] = []
        for bot in bots:
            try:
                await self._handle(bot)
                if bot.desired_state is BotState.RUNNING:
                    running.append(bot.id)
            except Exception as exc:
                await self._on_failure(bot, exc)
        async with self._stores() as store:
            now = self._clock.now()
            if running:
                await store.bots.heartbeat(running, now)
            await store.flags.set_worker_heartbeat(now)  # lets the API tell if the worker is alive
            await store.commit()

    async def _housekeeping(self, bots: list[Bot]) -> None:
        """Real-exchange upkeep that does not belong to any single candle.

        Settle orders of unknown outcome, notice stops that fired while we were away and, at
        a slower pace, compare the account with our books. Failures here are logged, never
        fatal: a flaky exchange must not stop the other bots.
        """
        if self._reconciler is None or self._executor is None:
            return
        now = self._clock.now()
        testnet = [
            b
            for b in bots
            if b.config.mode is ExecutionMode.TESTNET and b.observed_state is not BotState.ERROR
        ]
        if not testnet:
            return
        try:
            await self._reconciler.resolve_pending()
            if (
                self._last_stop_poll is None
                or now - self._last_stop_poll >= self._stop_poll_interval
            ):
                self._last_stop_poll = now
                for bot in testnet:
                    try:
                        await self._executor.sync_native_stop(bot)
                    except Exception:
                        logger.exception("stop sync failed for bot %s", bot.id)
            if (
                self._last_reconcile is None
                or now - self._last_reconcile >= self._reconcile_interval
            ):
                self._last_reconcile = now
                await self._reconciler.reconcile_accounts()
        except Exception:
            logger.exception("exchange housekeeping failed")

    async def _handle(self, bot: Bot) -> None:
        if bot.desired_state is BotState.RUNNING:
            if bot.observed_state is not BotState.RUNNING and not await self._start(bot):
                return
            retry_at = self._retry_at.get(bot.id)
            if retry_at is not None and self._clock.now() < retry_at:
                return
            await self._trader.process(bot)
            self._failures.pop(bot.id, None)
            self._retry_at.pop(bot.id, None)
        elif bot.desired_state is BotState.PAUSED:
            # An ERROR observation is kept (with its message) until the user starts the bot again.
            if bot.observed_state not in (BotState.PAUSED, BotState.ERROR):
                await self._set_observed(bot, BotState.PAUSED, "bot.paused")
        elif bot.observed_state is not BotState.STOPPED:
            await self._stop(bot)

    async def _testnet_problem(self, bot: Bot) -> str | None:
        """Why a testnet bot may not run, or None. Checked on every start."""
        if not self._testnet_enabled:
            return "testnet trading is disabled (set TESTNET_TRADING_ENABLED=true on the worker)"
        if self._resolver is None or bot.config.connection_id is None:
            return "testnet bot has no usable exchange connection"
        try:
            exchange = await self._resolver.exchange_for(bot.config.connection_id)
        except Exception as exc:
            return f"exchange connection unusable: {type(exc).__name__}: {exc}"
        if not exchange.capabilities.has_testnet:
            return f"{bot.config.exchange} has no testnet"
        return None

    async def _enter_error(self, bot: Bot, message: str) -> None:
        async with self._stores() as store:
            await store.bots.set_desired(bot.id, BotState.PAUSED)
            await store.bots.set_observed(bot.id, BotState.ERROR, message)
            await store.audit.add(
                AuditEvent(
                    "bot.error",
                    "bot",
                    str(bot.id),
                    actor="worker",
                    bot_id=bot.id,
                    payload={"error": message},
                )
            )
            await store.commit()
        bot.desired_state, bot.observed_state = BotState.PAUSED, BotState.ERROR

    async def _start(self, bot: Bot) -> bool:
        """Start (or resume) the bot. False when it was refused and put in the error state."""
        self._registry.create(bot.config.strategy_type, bot.config.strategy_params)  # validates
        if bot.config.mode is ExecutionMode.TESTNET and (
            problem := await self._testnet_problem(bot)
        ):
            await self._enter_error(bot, problem)
            return False
        resumed = bot.observed_state is BotState.PAUSED
        async with self._stores() as store:
            if await store.sessions.get_active(bot.id) is None:
                await store.sessions.add(
                    TradingSession(
                        id=self._ids.new_id(),
                        bot_id=bot.id,
                        config_version=bot.config_version,
                        status=SessionStatus.ACTIVE,
                        started_at=self._clock.now(),
                    )
                )
            await store.bots.set_observed(bot.id, BotState.RUNNING, None)
            await store.audit.add(
                AuditEvent(
                    "bot.resumed" if resumed else "bot.started",
                    "bot",
                    str(bot.id),
                    actor="worker",
                    bot_id=bot.id,
                    payload={"config_version": bot.config_version, "mode": bot.config.mode.value},
                )
            )
            await store.commit()
        bot.observed_state = BotState.RUNNING
        if bot.config.mode is ExecutionMode.TESTNET and self._reconciler and self._executor:
            # Catch up on anything that happened to our orders while the bot was not running.
            try:
                await self._reconciler.resolve_pending()
                await self._executor.sync_native_stop(bot)
            except Exception:
                logger.exception("start-up reconciliation failed for bot %s", bot.id)
        return True

    async def _stop(self, bot: Bot) -> None:
        async with self._stores() as store:
            session = await store.sessions.get_active(bot.id)
            if session is not None:
                await store.sessions.end(session.id, "stopped")
            await store.bots.set_observed(bot.id, BotState.STOPPED, None)
            await store.audit.add(
                AuditEvent("bot.stopped", "bot", str(bot.id), actor="worker", bot_id=bot.id)
            )
            await store.commit()
        self._failures.pop(bot.id, None)
        self._retry_at.pop(bot.id, None)

    async def _set_observed(self, bot: Bot, state: BotState, event: str) -> None:
        async with self._stores() as store:
            await store.bots.set_observed(bot.id, state, None)
            await store.audit.add(
                AuditEvent(event, "bot", str(bot.id), actor="worker", bot_id=bot.id)
            )
            await store.commit()

    async def _apply_kill_switch(self, bots: list[Bot], state: KillSwitchState) -> list[Bot]:
        async with self._stores() as store:
            for bot in bots:
                if bot.desired_state is BotState.RUNNING:
                    await store.bots.set_desired(bot.id, BotState.PAUSED)
                    await store.audit.add(
                        AuditEvent(
                            "bot.paused_by_kill_switch",
                            "bot",
                            str(bot.id),
                            actor="worker",
                            bot_id=bot.id,
                            payload={"reason": state.reason},
                        )
                    )
                    bot.desired_state = BotState.PAUSED
            await store.commit()
        return bots

    async def _on_failure(self, bot: Bot, exc: Exception) -> None:
        if isinstance(exc, _FATAL):
            logger.error("bot %s cannot continue: %s", bot.id, exc)
            await self._enter_error(bot, f"{type(exc).__name__}: {exc}"[:500])
            self._failures.pop(bot.id, None)
            self._retry_at.pop(bot.id, None)
            return
        count = self._failures.get(bot.id, 0) + 1
        self._failures[bot.id] = count
        logger.exception("bot %s failed (%d consecutive)", bot.id, count)
        if count < MAX_CONSECUTIVE_FAILURES:
            delay = min(_MAX_BACKOFF_SECONDS, 2**count)
            self._retry_at[bot.id] = self._clock.now() + timedelta(seconds=delay)
            return
        await self._enter_error(bot, f"{type(exc).__name__}: {exc}"[:500])
        self._failures.pop(bot.id, None)
        self._retry_at.pop(bot.id, None)
