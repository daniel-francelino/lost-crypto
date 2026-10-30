from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from modules.risk_management.domain.models import KillSwitchState
from modules.risk_management.infrastructure.orm import SystemFlagRow

KILL_SWITCH = "kill_switch"


class SqlAlchemySystemFlagsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_kill_switch(self) -> KillSwitchState:
        row = await self._session.get(SystemFlagRow, KILL_SWITCH)
        if row is None:
            return KillSwitchState()
        return KillSwitchState(active=row.active, reason=row.reason, changed_at=row.changed_at)

    async def set_kill_switch(self, active: bool, reason: str | None) -> KillSwitchState:
        stmt = insert(SystemFlagRow).values(
            key=KILL_SWITCH, active=active, reason=reason, changed_at=func.now()
        )
        await self._session.execute(
            stmt.on_conflict_do_update(
                index_elements=["key"],
                set_={"active": active, "reason": reason, "changed_at": func.now()},
            )
        )
        await self._session.flush()
        self._session.expire_all()
        return await self.get_kill_switch()
