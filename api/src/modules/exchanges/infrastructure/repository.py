from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from modules.exchanges.domain.connections import (
    ApiPermissions,
    ConnectionStatus,
    Environment,
    ExchangeConnection,
    permissions_from_dict,
    permissions_to_dict,
)
from modules.exchanges.infrastructure.orm import ExchangeConnectionRow, ReconciliationRunRow


def _to_connection(row: ExchangeConnectionRow) -> ExchangeConnection:
    return ExchangeConnection(
        id=row.id,
        exchange=row.exchange,
        environment=Environment(row.environment),
        label=row.label,
        api_key_hint=row.api_key_hint,
        status=ConnectionStatus(row.status),
        created_at=row.created_at,
        verified_at=row.verified_at,
        permissions=permissions_from_dict(row.permissions) if row.permissions else None,
        status_reason=row.status_reason,
        last_checked_at=row.last_checked_at,
        permission_warning=row.permission_warning,
    )


class SqlAlchemyConnectionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, connection: ExchangeConnection, sealed: bytes, key_id: str) -> bool:
        self._session.add(
            ExchangeConnectionRow(
                id=connection.id,
                exchange=connection.exchange,
                environment=connection.environment.value,
                label=connection.label,
                credentials_encrypted=sealed,
                key_id=key_id,
                api_key_hint=connection.api_key_hint,
                status=connection.status.value,
                created_at=connection.created_at,
            )
        )
        try:
            await self._session.flush()
        except IntegrityError:
            await self._session.rollback()
            return False
        return True

    async def get(self, connection_id: UUID) -> ExchangeConnection | None:
        row = await self._session.get(ExchangeConnectionRow, connection_id)
        return _to_connection(row) if row else None

    async def lock(self, connection_id: UUID) -> ExchangeConnection | None:
        result = await self._session.execute(
            select(ExchangeConnectionRow)
            .where(ExchangeConnectionRow.id == connection_id)
            .with_for_update()
        )
        row = result.scalar_one_or_none()
        return _to_connection(row) if row else None

    async def get_sealed(self, connection_id: UUID) -> bytes | None:
        result = await self._session.execute(
            select(ExchangeConnectionRow.credentials_encrypted).where(
                ExchangeConnectionRow.id == connection_id
            )
        )
        return result.scalar_one_or_none()

    async def list_connections(self) -> list[ExchangeConnection]:
        result = await self._session.execute(
            select(ExchangeConnectionRow).order_by(ExchangeConnectionRow.created_at)
        )
        return [_to_connection(r) for r in result.scalars()]

    async def list_pending(self) -> list[ExchangeConnection]:
        result = await self._session.execute(
            select(ExchangeConnectionRow)
            .where(ExchangeConnectionRow.status == ConnectionStatus.PENDING.value)
            .order_by(ExchangeConnectionRow.created_at)
        )
        return [_to_connection(r) for r in result.scalars()]

    async def list_active_live(self) -> list[ExchangeConnection]:
        result = await self._session.execute(
            select(ExchangeConnectionRow)
            .where(
                ExchangeConnectionRow.status == ConnectionStatus.ACTIVE.value,
                ExchangeConnectionRow.environment == Environment.LIVE.value,
            )
            .order_by(ExchangeConnectionRow.created_at)
        )
        return [_to_connection(r) for r in result.scalars()]

    async def record_check(
        self,
        connection_id: UUID,
        *,
        checked_at: datetime,
        permissions: ApiPermissions | None,
        reason: str | None,
        warning: str | None,
    ) -> None:
        await self._session.execute(
            update(ExchangeConnectionRow)
            .where(ExchangeConnectionRow.id == connection_id)
            .values(
                last_checked_at=checked_at,
                permissions=permissions_to_dict(permissions) if permissions else None,
                status_reason=reason,
                permission_warning=warning,
            )
        )

    async def set_status(
        self, connection_id: UUID, status: ConnectionStatus, verified_at: datetime | None
    ) -> None:
        await self._session.execute(
            update(ExchangeConnectionRow)
            .where(ExchangeConnectionRow.id == connection_id)
            .values(status=status.value, verified_at=verified_at)
        )


class SqlAlchemyReconciliationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(
        self, connection_id: UUID, started_at: datetime, status: str, details: dict[str, Any]
    ) -> None:
        self._session.add(
            ReconciliationRunRow(
                id=uuid4(),
                connection_id=connection_id,
                started_at=started_at,
                status=status,
                details=details,
            )
        )
        await self._session.flush()

    async def latest(self, connection_id: UUID) -> tuple[datetime, str, dict[str, Any]] | None:
        result = await self._session.execute(
            select(ReconciliationRunRow)
            .where(ReconciliationRunRow.connection_id == connection_id)
            .order_by(ReconciliationRunRow.started_at.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return None if row is None else (row.started_at, row.status, row.details)
