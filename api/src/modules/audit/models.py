from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AuditEvent:
    event_type: str  # e.g. "bot.started", "order.filled", "risk.daily_loss_breached"
    entity_type: str
    entity_id: str
    actor: str = "system"  # "api" for user commands, "worker" for the trading loop
    bot_id: UUID | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    occurred_at: datetime | None = None  # filled by the database on insert


class AuditRepository(Protocol):
    """Append-only: there is intentionally no update or delete."""

    async def add(self, event: AuditEvent) -> None: ...
    async def list_events(
        self, bot_id: UUID | None, limit: int, offset: int = 0, event_type: str | None = None
    ) -> list[AuditEvent]: ...
    async def count_all(
        self, bot_id: UUID | None, event_type: str | None = None, since: datetime | None = None
    ) -> int: ...
    async def count_events(
        self,
        bot_id: UUID,
        event_types: Sequence[str],
        before: datetime | None = None,
        since: datetime | None = None,
    ) -> int: ...

    async def list_events_since(
        self, bot_id: UUID, event_types: Sequence[str], since: datetime, limit: int
    ) -> list[AuditEvent]: ...

    async def latest_event_time(self, bot_id: UUID, event_type: str) -> datetime | None: ...
