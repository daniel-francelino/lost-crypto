"""Reconciles each bot's ``desired_state`` (set by the API) with what the worker is doing."""

import logging
from datetime import datetime, timedelta
from uuid import UUID

from core.clock import Clock
from core.ids import IdGenerator
from modules.audit.models import AuditEvent
from modules.bots.domain.models import Bot, BotState
from modules.risk_management.domain.models import KillSwitchState
from modules.strategies.domain.registry import StrategyRegistry
from modules.trading.application.trader import BotTrader, TradingStoreFactory
from modules.trading.domain.models import MAX_CONSECUTIVE_FAILURES, SessionStatus, TradingSession

logger = logging.getLogger(__name__)

_MAX_BACKOFF_SECONDS = 60


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
    ) -> None:
        self._stores = stores
        self._trader = trader
        self._registry = registry
        self._clock = clock
        self._ids = ids
        self._failures: dict[UUID, int] = {}
        self._retry_at: dict[UUID, datetime] = {}

    async def run_once(self) -> None:
        async with self._stores() as store:
            kill_switch = await store.flags.get_kill_switch()
            bots = await store.bots.list_active()
        if kill_switch.active:
            bots = await self._apply_kill_switch(bots, kill_switch)

        running: list[UUID] = []
        for bot in bots:
            try:
                await self._handle(bot)
                if bot.desired_state is BotState.RUNNING:
                    running.append(bot.id)
            except Exception as exc:
                await self._on_failure(bot, exc)
        if running:
            async with self._stores() as store:
                await store.bots.heartbeat(running, self._clock.now())
                await store.commit()

    async def _handle(self, bot: Bot) -> None:
        if bot.desired_state is BotState.RUNNING:
            if bot.observed_state is not BotState.RUNNING:
                await self._start(bot)
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

    async def _start(self, bot: Bot) -> None:
        self._registry.create(bot.config.strategy_type, bot.config.strategy_params)  # validates
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
        count = self._failures.get(bot.id, 0) + 1
        self._failures[bot.id] = count
        logger.exception("bot %s failed (%d consecutive)", bot.id, count)
        if count < MAX_CONSECUTIVE_FAILURES:
            delay = min(_MAX_BACKOFF_SECONDS, 2**count)
            self._retry_at[bot.id] = self._clock.now() + timedelta(seconds=delay)
            return
        message = f"{type(exc).__name__}: {exc}"[:500]
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
        self._failures.pop(bot.id, None)
        self._retry_at.pop(bot.id, None)
