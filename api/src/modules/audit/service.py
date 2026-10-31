from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from typing import Protocol
from uuid import UUID

from modules.audit.models import AuditEvent, AuditRepository


class AuditStore(Protocol):
    @property
    def audit(self) -> AuditRepository: ...


class AuditService:
    def __init__(self, stores: Callable[[], AbstractAsyncContextManager[AuditStore]]) -> None:
        self._stores = stores

    async def list_events(
        self,
        bot_id: UUID | None,
        limit: int = 100,
        offset: int = 0,
        event_type: str | None = None,
    ) -> tuple[list[AuditEvent], int]:
        """One window of the trail (newest first) and the total that matches the filters."""
        async with self._stores() as store:
            events = await store.audit.list_events(bot_id, limit, offset, event_type)
            return events, await store.audit.count_all(bot_id, event_type)
