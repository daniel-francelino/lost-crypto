import asyncio
import logging
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager, suppress
from datetime import datetime, timedelta
from typing import Protocol
from uuid import UUID

from core.clock import Clock
from core.errors import NotFoundError
from modules.bots.application.ports import BotRepository
from modules.market_data.application.updater import UpdateReport
from modules.notifications.application import conditions
from modules.notifications.application.evaluator import AlertEvaluator
from modules.notifications.application.ports import AlertStore
from modules.notifications.domain.models import (
    Alert,
    AlertKind,
    AlertSeverity,
    AlertSummary,
)
from modules.trading.application.status import StatusService

logger = logging.getLogger(__name__)

# The API watches the worker; the worker watches everything else (it cannot report its own death).
API_SCOPE = frozenset({AlertKind.WORKER_DOWN})
WORKER_SCOPE = frozenset(
    {
        AlertKind.BOT_STALE,
        AlertKind.BOT_ERROR,
        AlertKind.KILL_SWITCH_ACTIVE,
        AlertKind.CANDLES_STALE,
        AlertKind.EXCHANGE_RATE_LIMITED,
    }
)


class AlertNotFound(NotFoundError):
    pass


class MonitorStore(AlertStore, Protocol):
    @property
    def bots(self) -> BotRepository: ...


class AlertService:
    """API-side use cases: read alerts and mark them as read."""

    def __init__(
        self, stores: Callable[[], AbstractAsyncContextManager[AlertStore]], clock: Clock
    ) -> None:
        self._stores = stores
        self._clock = clock

    async def list_alerts(
        self,
        unread: bool,
        severity: AlertSeverity | None,
        bot_id: UUID | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Alert], int]:
        async with self._stores() as store:
            alerts = await store.alerts.list_alerts(unread, severity, bot_id, limit, offset)
            total = await store.alerts.count_alerts(unread, severity, bot_id)
        return alerts, total

    async def summary(self) -> AlertSummary:
        async with self._stores() as store:
            return await store.alerts.summary()

    async def mark_read(self, alert_id: int) -> None:
        async with self._stores() as store:
            if not await store.alerts.mark_read(alert_id, self._clock.now()):
                raise AlertNotFound(f"alert {alert_id} not found")
            await store.commit()

    async def mark_all_read(self) -> int:
        async with self._stores() as store:
            marked = await store.alerts.mark_all_read(self._clock.now())
            await store.commit()
        return marked


class AlertMonitor:
    """Feeds the evaluator. Failures are logged and swallowed: monitoring must never be the
    reason the worker or the API stops."""

    def __init__(
        self,
        stores: Callable[[], AbstractAsyncContextManager[MonitorStore]],
        status: StatusService,
        evaluator: AlertEvaluator,
        clock: Clock,
        interval: timedelta,
        retention: timedelta,
        update_report: Callable[[], UpdateReport] | None = None,
    ) -> None:
        self._stores = stores
        self._status = status
        self._evaluator = evaluator
        self._clock = clock
        self._interval = interval
        self._retention = retention
        self._update_report = update_report
        self._last_run: datetime | None = None

    async def run_worker_if_due(self) -> None:
        now = self._clock.now()
        if self._last_run is not None and now - self._last_run < self._interval:
            return
        self._last_run = now
        try:
            status = await self._status.system_status()
            async with self._stores() as store:
                active = await store.bots.list_active()
            firing = [
                *conditions.kill_switch(status),
                *conditions.bots(status, active),
                *(conditions.candles(self._update_report()) if self._update_report else []),
            ]
            await self._evaluator.sync(WORKER_SCOPE, firing, actor="worker")
        except Exception:
            logger.exception("alert evaluation failed")

    async def run_api_once(self) -> None:
        try:
            status = await self._status.system_status()
            await self._evaluator.sync(API_SCOPE, conditions.worker_down(status), actor="api")
            await self._purge()
        except Exception:
            logger.exception("alert evaluation failed")

    async def run_api_forever(self) -> None:
        with suppress(asyncio.CancelledError):
            while True:
                await self.run_api_once()
                await asyncio.sleep(self._interval.total_seconds())

    async def _purge(self) -> None:
        async with self._stores() as store:
            await store.alerts.purge(self._clock.now() - self._retention)
            await store.commit()
