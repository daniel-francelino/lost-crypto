from datetime import datetime

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from container import Container

router = APIRouter(prefix="/system", tags=["system"])


class KillSwitchIn(BaseModel):
    active: bool
    reason: str | None = Field(default=None, max_length=200)


class KillSwitchOut(BaseModel):
    active: bool
    reason: str | None
    changed_at: datetime | None


def _container(request: Request) -> Container:
    container: Container = request.app.state.container
    return container


@router.get("/kill-switch", response_model=KillSwitchOut)
async def get_kill_switch(request: Request) -> KillSwitchOut:
    state = await _container(request).kill_switch.get()
    return KillSwitchOut(active=state.active, reason=state.reason, changed_at=state.changed_at)


@router.put("/kill-switch", response_model=KillSwitchOut)
async def set_kill_switch(body: KillSwitchIn, request: Request) -> KillSwitchOut:
    """Emergency stop. While active, the worker pauses every running bot and no new entries
    are approved. Releasing it does not resume bots: start them again explicitly."""
    state = await _container(request).kill_switch.set(body.active, body.reason)
    return KillSwitchOut(active=state.active, reason=state.reason, changed_at=state.changed_at)
