from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from typing import Protocol

from modules.audit.models import AuditEvent, AuditRepository
from modules.risk_management.application.ports import SystemFlagsRepository
from modules.risk_management.domain.models import KillSwitchState


class KillSwitchStore(Protocol):
    @property
    def flags(self) -> SystemFlagsRepository: ...
    @property
    def audit(self) -> AuditRepository: ...

    async def commit(self) -> None: ...


class KillSwitchService:
    """Global emergency stop: while active, the worker pauses every running bot and no new
    entries are approved. Deactivating it does NOT resume bots; that is a deliberate step."""

    def __init__(self, stores: Callable[[], AbstractAsyncContextManager[KillSwitchStore]]) -> None:
        self._stores = stores

    async def get(self) -> KillSwitchState:
        async with self._stores() as store:
            return await store.flags.get_kill_switch()

    async def set(self, active: bool, reason: str | None) -> KillSwitchState:
        async with self._stores() as store:
            state = await store.flags.set_kill_switch(active, reason)
            await store.audit.add(
                AuditEvent(
                    "system.kill_switch_activated" if active else "system.kill_switch_released",
                    "system",
                    "kill_switch",
                    actor="api",
                    payload={"reason": reason},
                )
            )
            await store.commit()
        return state
