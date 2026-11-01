from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from typing import Any, Protocol
from uuid import UUID

from modules.audit.models import AuditEvent, AuditRepository

NOTE_EVENT = "note.added"


class AuditStore(Protocol):
    @property
    def audit(self) -> AuditRepository: ...

    async def commit(self) -> None: ...


class AuditService:
    def __init__(self, stores: Callable[[], AbstractAsyncContextManager[AuditStore]]) -> None:
        self._stores = stores

    async def list_events(
        self,
        bot_id: UUID | None,
        limit: int = 100,
        offset: int = 0,
        event_type: str | None = None,
        entity_id: str | None = None,
    ) -> tuple[list[AuditEvent], int]:
        """One window of the trail (newest first) and the total that matches the filters."""
        async with self._stores() as store:
            events = await store.audit.list_events(bot_id, limit, offset, event_type, entity_id)
            return events, await store.audit.count_all(bot_id, event_type, entity_id=entity_id)

    async def record(
        self,
        event_type: str,
        entity_type: str,
        entity_id: str,
        actor: str,
        payload: dict[str, Any],
    ) -> None:
        """Append one event outside any other transaction (for changes that live elsewhere)."""
        async with self._stores() as store:
            await store.audit.add(
                AuditEvent(event_type, entity_type, entity_id, actor=actor, payload=payload)
            )
            await store.commit()

    async def add_note(
        self, entity_type: str, entity_id: str, bot_id: UUID | None, actor: str, text: str
    ) -> None:
        """A free-text analysis note (why a strategy was paused or retired) as an audit event.
        Plain text only: callers must render it as text."""
        async with self._stores() as store:
            await store.audit.add(
                AuditEvent(
                    NOTE_EVENT,
                    entity_type,
                    entity_id,
                    actor=actor,
                    bot_id=bot_id,
                    payload={"text": text},
                )
            )
            await store.commit()
