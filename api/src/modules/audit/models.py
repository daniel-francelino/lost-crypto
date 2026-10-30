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
    async def list_events(self, bot_id: UUID | None, limit: int) -> list[AuditEvent]: ...
