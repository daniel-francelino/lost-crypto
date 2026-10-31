from datetime import datetime

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from container import Container
from core.config import AppEnv

router = APIRouter(prefix="/system", tags=["system"])


class KillSwitchIn(BaseModel):
    active: bool
    reason: str | None = Field(default=None, max_length=200)


class KillSwitchOut(BaseModel):
    active: bool
    reason: str | None
    changed_at: datetime | None


class WorkerOut(BaseModel):
    alive: bool
    last_heartbeat_at: datetime | None
    age_seconds: float | None


class StaleBotOut(BaseModel):
    bot_id: str
    name: str
    last_heartbeat_at: datetime | None
    age_seconds: float | None


class SystemStatusOut(BaseModel):
    worker: WorkerOut
    kill_switch: KillSwitchOut
    bots_by_state: dict[str, int]
    stale_bots: list[StaleBotOut]
    exchanges: list[str]


class CapabilitiesOut(BaseModel):
    """What this deployment allows, so the UI can explain instead of letting a user try and fail.
    It reflects the API process's configuration; the worker enforces its own on every pass."""

    environment: AppEnv
    testnet_trading_enabled: bool
    live_trading_enabled: bool
    live_available: bool
    live_blockers: list[str]
    live_min_paper_days: int
    live_approval_minutes: int
    exchanges: list[str]
    strategies: list[str]


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


@router.get("/capabilities", response_model=CapabilitiesOut)
async def get_capabilities(request: Request) -> CapabilitiesOut:
    """Is live trading possible here, and if not, what is missing? Contains no secrets."""
    container = _container(request)
    settings = container.settings
    blockers = []
    if not settings.live_trading_enabled:
        blockers.append("LIVE_TRADING_ENABLED is off")
    if settings.app_env is not AppEnv.PROD:
        blockers.append("APP_ENV is not prod")
    if not settings.live_caps_configured:
        blockers.append("the live hard caps (LIVE_MAX_*) are not all set")
    return CapabilitiesOut(
        environment=settings.app_env,
        testnet_trading_enabled=settings.testnet_trading_enabled,
        live_trading_enabled=settings.live_trading_enabled,
        live_available=not blockers,
        live_blockers=blockers,
        live_min_paper_days=settings.live_min_paper_days,
        live_approval_minutes=settings.live_approval_minutes,
        exchanges=container.exchanges.exchange_ids(),
        strategies=[strategy.TYPE_KEY for strategy in container.registry.list()],
    )


@router.get("/status", response_model=SystemStatusOut)
async def get_status(request: Request) -> SystemStatusOut:
    """Is the worker alive and is every running bot advancing? Poll this from a monitor."""
    status = await _container(request).status.system_status()
    return SystemStatusOut(
        worker=WorkerOut(
            alive=status.worker.alive,
            last_heartbeat_at=status.worker.last_heartbeat_at,
            age_seconds=status.worker.age_seconds,
        ),
        kill_switch=KillSwitchOut(
            active=status.kill_switch.active,
            reason=status.kill_switch.reason,
            changed_at=status.kill_switch.changed_at,
        ),
        bots_by_state=status.bots_by_state,
        stale_bots=[
            StaleBotOut(
                bot_id=b.bot_id,
                name=b.name,
                last_heartbeat_at=b.last_heartbeat_at,
                age_seconds=b.age_seconds,
            )
            for b in status.stale_bots
        ],
        exchanges=status.exchanges,
    )
