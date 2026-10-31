from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Query, Request, Response
from pydantic import BaseModel

from container import Container
from core.pagination import Offset, set_total

router = APIRouter(prefix="/audit-events", tags=["audit"])


class AuditEventOut(BaseModel):
    occurred_at: datetime | None
    actor: str
    event_type: str
    entity_type: str
    entity_id: str
    bot_id: UUID | None
    payload: dict[str, Any]


@router.get("", response_model=list[AuditEventOut])
async def list_audit_events(
    request: Request,
    response: Response,
    bot_id: UUID | None = None,
    event_type: Annotated[str | None, Query(max_length=100)] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Offset = 0,
) -> list[AuditEventOut]:
    """Append-only trail of commands, state changes, orders and risk events (newest first).
    The size of the whole trail that matches is in ``X-Total-Count``."""
    container: Container = request.app.state.container
    events, total = await container.audit.list_events(bot_id, limit, offset, event_type)
    set_total(response, total)
    return [
        AuditEventOut(
            occurred_at=e.occurred_at,
            actor=e.actor,
            event_type=e.event_type,
            entity_type=e.entity_type,
            entity_id=e.entity_id,
            bot_id=e.bot_id,
            payload=e.payload,
        )
        for e in events
    ]
