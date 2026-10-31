from collections.abc import Collection, Mapping
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from modules.audit.models import AuditRepository
from modules.notifications.domain.models import (
    Alert,
    AlertKind,
    AlertSeverity,
    AlertSummary,
)


class AlertRepository(Protocol):
    async def add(
        self,
        kind: AlertKind,
        severity: AlertSeverity,
        dedupe_key: str,
        message: str,
        bot_id: UUID | None,
        payload: Mapping[str, Any],
        opened_at: datetime,
    ) -> Alert: ...

    async def list_open(self, kinds: Collection[AlertKind]) -> list[Alert]: ...
    async def latest_for_key(self, dedupe_key: str) -> Alert | None: ...
    async def update_open(
        self, alert_id: int, severity: AlertSeverity, message: str, payload: Mapping[str, Any]
    ) -> None: ...
    async def reopen(
        self, alert_id: int, severity: AlertSeverity, message: str, payload: Mapping[str, Any]
    ) -> None:
        """Clears ``resolved_at`` and ``read_at``: a flapping condition is one episode."""
        ...

    async def resolve(self, alert_id: int, at: datetime) -> None: ...
    async def list_alerts(
        self,
        unread: bool,
        severity: AlertSeverity | None,
        bot_id: UUID | None,
        limit: int,
        offset: int,
    ) -> list[Alert]: ...

    async def count_alerts(
        self, unread: bool, severity: AlertSeverity | None, bot_id: UUID | None
    ) -> int: ...

    async def summary(self) -> AlertSummary: ...
    async def mark_read(self, alert_id: int, at: datetime) -> bool: ...
    async def mark_all_read(self, at: datetime) -> int: ...
    async def purge(self, resolved_before: datetime) -> int:
        """Deletes alerts that are resolved and already read, resolved before the cutoff."""
        ...


class AlertStore(Protocol):
    @property
    def alerts(self) -> AlertRepository: ...
    @property
    def audit(self) -> AuditRepository: ...

    async def commit(self) -> None: ...
