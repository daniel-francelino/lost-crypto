from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import datetime, timedelta

from core.clock import Clock
from modules.bots.domain.models import BotState
from modules.risk_management.domain.models import KillSwitchState
from modules.trading.application.ports import TradingStore


@dataclass(frozen=True, slots=True)
class WorkerStatus:
    alive: bool
    last_heartbeat_at: datetime | None
    age_seconds: float | None


@dataclass(frozen=True, slots=True)
class StaleBot:
    bot_id: str
    name: str
    last_heartbeat_at: datetime | None
    age_seconds: float | None


@dataclass(frozen=True, slots=True)
class SystemStatus:
    worker: WorkerStatus
    kill_switch: KillSwitchState
    bots_by_state: dict[str, int]
    stale_bots: list[StaleBot]
    exchanges: list[str]


class StatusService:
    """Is the worker alive, and is every bot that should be running actually advancing?"""

    def __init__(
        self,
        stores: Callable[[], AbstractAsyncContextManager[TradingStore]],
        clock: Clock,
        exchange_ids: Callable[[], list[str]],
        stale_after: timedelta,
    ) -> None:
        self._stores = stores
        self._clock = clock
        self._exchange_ids = exchange_ids
        self._stale_after = stale_after

    async def system_status(self) -> SystemStatus:
        now = self._clock.now()
        async with self._stores() as store:
            heartbeat = await store.flags.get_worker_heartbeat()
            kill_switch = await store.flags.get_kill_switch()
            bots = await store.bots.list_bots(500)

        def age(moment: datetime | None) -> float | None:
            return None if moment is None else (now - moment).total_seconds()

        worker_age = age(heartbeat)
        counts: dict[str, int] = {}
        stale: list[StaleBot] = []
        for bot in bots:
            counts[bot.observed_state.value] = counts.get(bot.observed_state.value, 0) + 1
            bot_age = age(bot.last_heartbeat_at)
            if bot.observed_state is BotState.RUNNING and (
                bot_age is None or bot_age > self._stale_after.total_seconds()
            ):
                stale.append(StaleBot(str(bot.id), bot.config.name, bot.last_heartbeat_at, bot_age))
        return SystemStatus(
            worker=WorkerStatus(
                alive=worker_age is not None and worker_age <= self._stale_after.total_seconds(),
                last_heartbeat_at=heartbeat,
                age_seconds=worker_age,
            ),
            kill_switch=kill_switch,
            bots_by_state=counts,
            stale_bots=stale,
            exchanges=self._exchange_ids(),
        )
