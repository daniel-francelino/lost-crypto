from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from modules.risk_management.domain.models import BackupRecord, KillSwitchState
from modules.risk_management.infrastructure.orm import BackupRunRow, SystemFlagRow

KILL_SWITCH = "kill_switch"
WORKER_HEARTBEAT = "worker_heartbeat"
CLOCK_SKEW = "clock_skew_ms"  # the value is kept in ``reason`` (a small flag table, no schema)


class SqlAlchemySystemFlagsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_kill_switch(self) -> KillSwitchState:
        row = await self._session.get(SystemFlagRow, KILL_SWITCH)
        if row is None:
            return KillSwitchState()
        return KillSwitchState(
            active=row.active,
            reason=row.reason,
            changed_at=row.changed_at,
            close_futures_positions=row.close_futures_positions,
        )

    async def set_kill_switch(
        self, active: bool, reason: str | None, close_futures_positions: bool | None = None
    ) -> KillSwitchState:
        stmt = insert(SystemFlagRow).values(
            key=KILL_SWITCH,
            active=active,
            reason=reason,
            changed_at=func.now(),
            close_futures_positions=bool(close_futures_positions),
        )
        await self._session.execute(
            stmt.on_conflict_do_update(
                index_elements=["key"],
                set_={
                    "active": active,
                    "reason": reason,
                    "changed_at": func.now(),
                    "close_futures_positions": (
                        SystemFlagRow.close_futures_positions
                        if close_futures_positions is None
                        else close_futures_positions
                    ),
                },
            )
        )
        await self._session.flush()
        self._session.expire_all()
        return await self.get_kill_switch()

    async def set_worker_heartbeat(self, at: datetime) -> None:
        stmt = insert(SystemFlagRow).values(
            key=WORKER_HEARTBEAT, active=True, reason=None, changed_at=at
        )
        await self._session.execute(
            stmt.on_conflict_do_update(index_elements=["key"], set_={"changed_at": at})
        )

    async def get_worker_heartbeat(self) -> datetime | None:
        row = await self._session.get(SystemFlagRow, WORKER_HEARTBEAT)
        return row.changed_at if row else None

    async def set_clock_skew(self, skew_ms: int, at: datetime) -> None:
        stmt = insert(SystemFlagRow).values(
            key=CLOCK_SKEW, active=True, reason=str(skew_ms), changed_at=at
        )
        await self._session.execute(
            stmt.on_conflict_do_update(
                index_elements=["key"], set_={"reason": str(skew_ms), "changed_at": at}
            )
        )

    async def get_clock_skew(self) -> tuple[int, datetime] | None:
        row = await self._session.get(SystemFlagRow, CLOCK_SKEW)
        if row is None or row.reason is None:
            return None
        return int(row.reason), row.changed_at

    async def add_backup_record(self, record: BackupRecord) -> None:
        self._session.add(
            BackupRunRow(
                kind=record.kind,
                at=record.at,
                ok=record.ok,
                file=record.file,
                size_bytes=record.size_bytes,
                checksum=record.checksum,
                detail=record.detail,
            )
        )
        await self._session.flush()

    async def latest_backup_record(self, kind: str) -> BackupRecord | None:
        result = await self._session.execute(
            select(BackupRunRow)
            .where(BackupRunRow.kind == kind)
            .order_by(BackupRunRow.at.desc(), BackupRunRow.id.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return BackupRecord(
            row.kind, row.at, row.ok, row.file, row.size_bytes, row.checksum, row.detail
        )
