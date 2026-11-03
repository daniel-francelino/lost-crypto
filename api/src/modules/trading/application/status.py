from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal

from core.clock import Clock
from modules.bots.domain.models import Bot, BotState
from modules.exchanges.domain.models import TradingProduct
from modules.execution.domain.orders import OrderStatus
from modules.risk_management.domain.models import BackupRecord, KillSwitchState
from modules.trading.application.ports import TradingStore
from modules.trading.application.trader import MAX_LIVE_CLOCK_SKEW_MS

CLOCK_WARN_MS = 1000
BACKUP_OVERDUE_AFTER = timedelta(hours=26)  # a daily backup, with some slack


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
class UnprotectedPosition:
    """An exchange position with no stop resting on the exchange: exposed while the worker is
    down, since only an exchange-side stop survives an outage (book 1 ch. 4, O2)."""

    bot_id: str
    name: str
    symbol: str
    mode: str
    quantity: Decimal
    stop_price: Decimal | None  # watched by the worker only, when set
    product: str = TradingProduct.SPOT.value


@dataclass(frozen=True, slots=True)
class ClockStatus:
    skew_ms: int | None
    measured_at: datetime | None
    warning: bool  # beyond CLOCK_WARN_MS
    blocking_live: bool  # beyond the trader's limit: no new live positions


@dataclass(frozen=True, slots=True)
class BackupStatus:
    last_backup: BackupRecord | None
    last_restore_check: BackupRecord | None
    overdue: bool  # no successful backup in BACKUP_OVERDUE_AFTER, or the last restore failed


@dataclass(frozen=True, slots=True)
class SystemStatus:
    worker: WorkerStatus
    kill_switch: KillSwitchState
    bots_by_state: dict[str, int]
    stale_bots: list[StaleBot]
    exchanges: list[str]
    unprotected_positions: list[UnprotectedPosition] = field(default_factory=list)
    clock: ClockStatus | None = None
    backup: BackupStatus | None = None


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

    async def worker_status(self) -> WorkerStatus:
        """Only the worker's liveness: cheap enough for an external monitor to poll."""
        now = self._clock.now()
        async with self._stores() as store:
            heartbeat = await store.flags.get_worker_heartbeat()
        age = None if heartbeat is None else (now - heartbeat).total_seconds()
        return WorkerStatus(
            alive=age is not None and age <= self._stale_after.total_seconds(),
            last_heartbeat_at=heartbeat,
            age_seconds=age,
        )

    async def system_status(self) -> SystemStatus:
        now = self._clock.now()
        async with self._stores() as store:
            heartbeat = await store.flags.get_worker_heartbeat()
            kill_switch = await store.flags.get_kill_switch()
            bots = await store.bots.list_bots(500)
            unprotected = await self._unprotected(store, bots)
            skew = await store.flags.get_clock_skew()
            backup = await store.flags.latest_backup_record("backup")
            restore = await store.flags.latest_backup_record("restore_check")

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
            unprotected_positions=unprotected,
            clock=_clock_status(skew),
            backup=BackupStatus(
                last_backup=backup,
                last_restore_check=restore,
                overdue=backup is None
                or not backup.ok
                or now - backup.at > BACKUP_OVERDUE_AFTER
                or (restore is not None and not restore.ok),
            ),
        )

    @staticmethod
    async def _unprotected(store: TradingStore, bots: list[Bot]) -> list[UnprotectedPosition]:
        found: list[UnprotectedPosition] = []
        for bot in bots:
            if not bot.config.mode.uses_exchange:
                continue  # paper money cannot be lost in an outage
            if bot.config.product is TradingProduct.LINEAR_PERPETUAL:
                ledger = await store.perpetual_portfolio.get(bot.id)
                if ledger is None or ledger.position is None:
                    continue
                position = ledger.position
                stop_id = ledger.stop_order_client_id
                stop = (
                    await store.orders.get_by_client_id(bot.id, stop_id)
                    if stop_id is not None
                    else None
                )
                if stop is None or stop.status not in {
                    OrderStatus.OPEN,
                    OrderStatus.PARTIALLY_FILLED,
                }:
                    found.append(
                        UnprotectedPosition(
                            str(bot.id),
                            bot.config.name,
                            bot.config.symbol,
                            bot.config.mode.value,
                            position.quantity,
                            position.stop_price,
                            bot.config.product.value,
                        )
                    )
                continue
            portfolio = await store.portfolio.get(bot.id)
            if portfolio is None or portfolio.quantity <= 0:
                continue
            if portfolio.stop_order_client_id is None:
                found.append(
                    UnprotectedPosition(
                        str(bot.id),
                        bot.config.name,
                        bot.config.symbol,
                        bot.config.mode.value,
                        portfolio.quantity,
                        portfolio.stop_price,
                    )
                )
        return found


def _clock_status(skew: tuple[int, datetime] | None) -> ClockStatus:
    if skew is None:
        return ClockStatus(None, None, False, False)
    ms, at = skew
    return ClockStatus(ms, at, abs(ms) > CLOCK_WARN_MS, abs(ms) > MAX_LIVE_CLOCK_SKEW_MS)
