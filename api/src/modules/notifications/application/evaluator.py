import logging
from collections.abc import Callable, Collection, Sequence
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass, replace
from datetime import timedelta

from core.clock import Clock
from modules.audit.models import AuditEvent
from modules.notifications.application.ports import AlertStore
from modules.notifications.domain.models import Alert, AlertKind, AlertSeverity, Condition

logger = logging.getLogger(__name__)

AlertStoreFactory = Callable[[], AbstractAsyncContextManager[AlertStore]]


@dataclass(frozen=True, slots=True)
class SyncResult:
    opened: int
    resolved: int


class AlertEvaluator:
    """Turns the conditions firing right now into alert episodes.

    One open alert per ``dedupe_key``: a condition that keeps firing changes nothing but the
    message; a condition that stops firing resolves its alert; one that comes back within the
    cooldown reopens the same alert instead of adding a new one (no flapping noise).
    """

    def __init__(self, stores: AlertStoreFactory, clock: Clock, cooldown: timedelta) -> None:
        self._stores = stores
        self._clock = clock
        self._cooldown = cooldown

    async def sync(
        self, scope: Collection[AlertKind], firing: Sequence[Condition], actor: str
    ) -> SyncResult:
        """Reconcile the open alerts of ``scope`` kinds with ``firing``. Conditions of other
        kinds are ignored, so independent evaluators can share the table."""
        now = self._clock.now()
        by_key = {c.dedupe_key: c for c in firing if c.kind in scope}
        opened = resolved = 0
        async with self._stores() as store:
            open_alerts = {a.dedupe_key: a for a in await store.alerts.list_open(scope)}
            for key, condition in by_key.items():
                existing = open_alerts.get(key)
                if existing is not None:
                    if _changed(existing, condition):
                        await store.alerts.update_open(
                            existing.id, condition.severity, condition.message, condition.payload
                        )
                    continue
                alert = await self._open(store, condition)
                opened += 1
                if alert.severity is AlertSeverity.CRITICAL:
                    await store.audit.add(_audit("alert.opened", alert, actor))
            for key, alert in open_alerts.items():
                if key in by_key:
                    continue
                await store.alerts.resolve(alert.id, now)
                resolved += 1
                if alert.severity is AlertSeverity.CRITICAL:
                    await store.audit.add(_audit("alert.resolved", alert, actor))
            await store.commit()
        return SyncResult(opened, resolved)

    async def _open(self, store: AlertStore, condition: Condition) -> Alert:
        now = self._clock.now()
        latest = await store.alerts.latest_for_key(condition.dedupe_key)
        if (
            latest is not None
            and latest.resolved_at is not None
            and now - latest.resolved_at < self._cooldown
        ):
            await store.alerts.reopen(
                latest.id, condition.severity, condition.message, condition.payload
            )
            return replace(
                latest,
                severity=condition.severity,
                message=condition.message,
                payload=condition.payload,
                resolved_at=None,
                read_at=None,
            )
        return await store.alerts.add(
            condition.kind,
            condition.severity,
            condition.dedupe_key,
            condition.message,
            condition.bot_id,
            condition.payload,
            now,
        )


def _changed(alert: Alert, condition: Condition) -> bool:
    return (
        alert.severity is not condition.severity
        or alert.message != condition.message
        or dict(alert.payload) != dict(condition.payload)
    )


def _audit(event_type: str, alert: Alert, actor: str) -> AuditEvent:
    return AuditEvent(
        event_type=event_type,
        entity_type="alert",
        entity_id=str(alert.id),
        actor=actor,
        bot_id=alert.bot_id,
        payload={
            "kind": alert.kind.value,
            "severity": alert.severity.value,
            "message": alert.message,
        },
    )
