from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Query, Request, Response, status
from pydantic import BaseModel

from container import Container
from core.pagination import Offset, set_total
from modules.notifications.domain.models import Alert, AlertKind, AlertSeverity

router = APIRouter(prefix="/alerts", tags=["alerts"])


class AlertOut(BaseModel):
    id: int
    kind: AlertKind
    severity: AlertSeverity
    message: str
    bot_id: UUID | None
    payload: dict[str, Any]
    opened_at: datetime
    resolved_at: datetime | None
    read_at: datetime | None


class AlertSummaryOut(BaseModel):
    unread: int
    open: int
    critical_open: int


class MarkedOut(BaseModel):
    marked: int


def _container(request: Request) -> Container:
    container: Container = request.app.state.container
    return container


def _out(alert: Alert) -> AlertOut:
    return AlertOut(
        id=alert.id,
        kind=alert.kind,
        severity=alert.severity,
        message=alert.message,
        bot_id=alert.bot_id,
        payload=dict(alert.payload),
        opened_at=alert.opened_at,
        resolved_at=alert.resolved_at,
        read_at=alert.read_at,
    )


@router.get("", response_model=list[AlertOut])
async def list_alerts(
    request: Request,
    response: Response,
    unread: bool = False,
    severity: AlertSeverity | None = None,
    bot_id: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Offset = 0,
) -> list[AlertOut]:
    """Failure alerts, newest first. An alert stays until it is resolved and read; the size of
    the whole list that matches is in ``X-Total-Count``."""
    alerts, total = await _container(request).alerts.list_alerts(
        unread, severity, bot_id, limit, offset
    )
    set_total(response, total)
    return [_out(a) for a in alerts]


@router.get("/summary", response_model=AlertSummaryOut)
async def get_alert_summary(request: Request) -> AlertSummaryOut:
    """Unread alerts and the alerts still open (without resolution), for the header indicator."""
    summary = await _container(request).alerts.summary()
    return AlertSummaryOut(
        unread=summary.unread, open=summary.open, critical_open=summary.critical_open
    )


@router.post("/read-all", response_model=MarkedOut)
async def mark_all_alerts_read(request: Request) -> MarkedOut:
    return MarkedOut(marked=await _container(request).alerts.mark_all_read())


@router.post("/{alert_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_alert_read(alert_id: int, request: Request) -> Response:
    await _container(request).alerts.mark_read(alert_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
