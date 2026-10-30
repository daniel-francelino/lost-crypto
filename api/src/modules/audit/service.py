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

    async def list_events(self, bot_id: UUID | None, limit: int = 100) -> list[AuditEvent]:
        async with self._stores() as store:
            return await store.audit.list_events(bot_id, limit)
