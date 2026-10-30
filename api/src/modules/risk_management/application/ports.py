from typing import Protocol

from modules.risk_management.domain.models import KillSwitchState


class SystemFlagsRepository(Protocol):
    async def get_kill_switch(self) -> KillSwitchState: ...
    async def set_kill_switch(self, active: bool, reason: str | None) -> KillSwitchState: ...
