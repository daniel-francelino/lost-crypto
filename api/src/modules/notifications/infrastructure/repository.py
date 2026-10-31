from collections.abc import Collection, Mapping
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from modules.notifications.domain.models import (
    Alert,
    AlertKind,
    AlertSeverity,
    AlertSummary,
)
from modules.notifications.infrastructure.orm import AlertRow


class SqlAlchemyAlertRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(
        self,
        kind: AlertKind,
        severity: AlertSeverity,
        dedupe_key: str,
        message: str,
        bot_id: UUID | None,
        payload: Mapping[str, Any],
        opened_at: datetime,
    ) -> Alert:
        row = AlertRow(
            kind=kind.value,
            severity=severity.value,
            dedupe_key=dedupe_key,
            message=message,
            bot_id=bot_id,
            payload=dict(payload),
            opened_at=opened_at,
        )
        self._session.add(row)
        await self._session.flush()
        return _to_alert(row)

    async def list_open(self, kinds: Collection[AlertKind]) -> list[Alert]:
        result = await self._session.execute(
            select(AlertRow)
            .where(AlertRow.resolved_at.is_(None), AlertRow.kind.in_([k.value for k in kinds]))
            .order_by(AlertRow.id)
        )
        return [_to_alert(r) for r in result.scalars()]

    async def latest_for_key(self, dedupe_key: str) -> Alert | None:
        result = await self._session.execute(
            select(AlertRow)
            .where(AlertRow.dedupe_key == dedupe_key)
            .order_by(AlertRow.id.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return _to_alert(row) if row is not None else None

    async def update_open(
        self, alert_id: int, severity: AlertSeverity, message: str, payload: Mapping[str, Any]
    ) -> None:
        await self._session.execute(
            update(AlertRow)
            .where(AlertRow.id == alert_id)
            .values(severity=severity.value, message=message, payload=dict(payload))
        )

    async def reopen(
        self, alert_id: int, severity: AlertSeverity, message: str, payload: Mapping[str, Any]
    ) -> None:
        await self._session.execute(
            update(AlertRow)
            .where(AlertRow.id == alert_id)
            .values(
                severity=severity.value,
                message=message,
                payload=dict(payload),
                resolved_at=None,
                read_at=None,
            )
        )

    async def resolve(self, alert_id: int, at: datetime) -> None:
        await self._session.execute(
            update(AlertRow).where(AlertRow.id == alert_id).values(resolved_at=at)
        )

    async def list_alerts(
        self,
        unread: bool,
        severity: AlertSeverity | None,
        bot_id: UUID | None,
        limit: int,
        offset: int,
    ) -> list[Alert]:
        result = await self._session.execute(
            select(AlertRow)
            .where(*_filters(unread, severity, bot_id))
            .order_by(AlertRow.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return [_to_alert(r) for r in result.scalars()]

    async def count_alerts(
        self, unread: bool, severity: AlertSeverity | None, bot_id: UUID | None
    ) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(AlertRow).where(*_filters(unread, severity, bot_id))
        )
        return int(result.scalar_one())

    async def summary(self) -> AlertSummary:
        result = await self._session.execute(
            select(
                func.count().filter(AlertRow.read_at.is_(None)),
                func.count().filter(AlertRow.resolved_at.is_(None)),
                func.count().filter(
                    AlertRow.resolved_at.is_(None),
                    AlertRow.severity == AlertSeverity.CRITICAL.value,
                ),
            ).select_from(AlertRow)
        )
        unread, open_, critical_open = result.one()
        return AlertSummary(int(unread), int(open_), int(critical_open))

    async def mark_read(self, alert_id: int, at: datetime) -> bool:
        result = await self._session.execute(
            update(AlertRow)
            .where(AlertRow.id == alert_id)
            .values(read_at=func.coalesce(AlertRow.read_at, at))
            .returning(AlertRow.id)
        )
        return result.first() is not None

    async def mark_all_read(self, at: datetime) -> int:
        result = await self._session.execute(
            update(AlertRow)
            .where(AlertRow.read_at.is_(None))
            .values(read_at=at)
            .returning(AlertRow.id)
        )
        return len(result.all())

    async def purge(self, resolved_before: datetime) -> int:
        result = await self._session.execute(
            delete(AlertRow)
            .where(AlertRow.resolved_at < resolved_before, AlertRow.read_at.is_not(None))
            .returning(AlertRow.id)
        )
        return len(result.all())


def _filters(
    unread: bool, severity: AlertSeverity | None, bot_id: UUID | None
) -> list[ColumnElement[bool]]:
    filters: list[ColumnElement[bool]] = []
    if unread:
        filters.append(AlertRow.read_at.is_(None))
    if severity is not None:
        filters.append(AlertRow.severity == severity.value)
    if bot_id is not None:
        filters.append(AlertRow.bot_id == bot_id)
    return filters


def _to_alert(row: AlertRow) -> Alert:
    return Alert(
        id=row.id,
        kind=AlertKind(row.kind),
        severity=AlertSeverity(row.severity),
        dedupe_key=row.dedupe_key,
        message=row.message,
        bot_id=row.bot_id,
        payload=row.payload,
        opened_at=row.opened_at,
        resolved_at=row.resolved_at,
        read_at=row.read_at,
    )
