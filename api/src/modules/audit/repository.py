from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from modules.audit.models import AuditEvent
from modules.audit.orm import AuditEventRow


class SqlAlchemyAuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, event: AuditEvent) -> None:
        self._session.add(
            AuditEventRow(
                actor=event.actor,
                event_type=event.event_type,
                entity_type=event.entity_type,
                entity_id=event.entity_id,
                bot_id=event.bot_id,
                payload=event.payload,
            )
        )
        await self._session.flush()

    async def list_events(self, bot_id: UUID | None, limit: int) -> list[AuditEvent]:
        query = select(AuditEventRow).order_by(AuditEventRow.id.desc()).limit(limit)
        if bot_id is not None:
            query = query.where(AuditEventRow.bot_id == bot_id)
        return [
            AuditEvent(
                event_type=r.event_type,
                entity_type=r.entity_type,
                entity_id=r.entity_id,
                actor=r.actor,
                bot_id=r.bot_id,
                payload=r.payload,
                occurred_at=r.occurred_at,
            )
            for r in (await self._session.execute(query)).scalars()
        ]
