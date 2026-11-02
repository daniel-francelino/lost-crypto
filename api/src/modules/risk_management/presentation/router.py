from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from container import Container
from core.config import AppEnv
from modules.risk_management.domain.models import BackupRecord

router = APIRouter(prefix="/system", tags=["system"])


class KillSwitchIn(BaseModel):
    active: bool
    reason: str | None = Field(default=None, max_length=200)
    close_futures_positions: bool = Field(
        default=False,
        description=(
            "When activating, cancel opening Futures orders and close tracked Demo positions."
        ),
    )


class KillSwitchOut(BaseModel):
    active: bool
    reason: str | None
    changed_at: datetime | None
    close_futures_positions: bool = False


class WorkerOut(BaseModel):
    alive: bool
    last_heartbeat_at: datetime | None
    age_seconds: float | None


class StaleBotOut(BaseModel):
    bot_id: str
    name: str
    last_heartbeat_at: datetime | None
    age_seconds: float | None


class UnprotectedPositionOut(BaseModel):
    bot_id: str
    name: str
    symbol: str
    mode: str
    quantity: Decimal
    stop_price: Decimal | None = Field(
        description="Stop watched by the worker only (none on the exchange), when set."
    )


class ClockOut(BaseModel):
    skew_ms: int | None = Field(description="Local clock minus the exchange's, in ms.")
    measured_at: datetime | None
    warning: bool = Field(description="Beyond 1 s.")
    blocking_live: bool = Field(description="Beyond 5 s: no new live positions are opened.")


class BackupRecordOut(BaseModel):
    at: datetime
    ok: bool
    file: str | None
    size_bytes: int | None
    detail: str | None


class BackupOut(BaseModel):
    last_backup: BackupRecordOut | None
    last_restore_check: BackupRecordOut | None
    overdue: bool = Field(
        description="No successful backup in 26 h, or the last restore check failed."
    )


class SystemStatusOut(BaseModel):
    worker: WorkerOut
    kill_switch: KillSwitchOut
    bots_by_state: dict[str, int]
    stale_bots: list[StaleBotOut]
    exchanges: list[str]
    unprotected_positions: list[UnprotectedPositionOut] = Field(
        default_factory=list,
        description="Testnet/live positions with no stop resting on the exchange: exposed "
        "while the worker is down.",
    )
    clock: ClockOut | None = None
    backup: BackupOut | None = None


def _record(record: BackupRecord | None) -> BackupRecordOut | None:
    if record is None:
        return None
    return BackupRecordOut(
        at=record.at,
        ok=record.ok,
        file=record.file,
        size_bytes=record.size_bytes,
        detail=record.detail,
    )


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
    return KillSwitchOut(
        active=state.active,
        reason=state.reason,
        changed_at=state.changed_at,
        close_futures_positions=state.close_futures_positions,
    )


@router.put("/kill-switch", response_model=KillSwitchOut)
async def set_kill_switch(body: KillSwitchIn, request: Request) -> KillSwitchOut:
    """Pause entries; optionally cancel opening Futures orders and close tracked positions."""
    state = await _container(request).kill_switch.set(
        body.active, body.reason, body.close_futures_positions
    )
    return KillSwitchOut(
        active=state.active,
        reason=state.reason,
        changed_at=state.changed_at,
        close_futures_positions=state.close_futures_positions,
    )


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
            close_futures_positions=status.kill_switch.close_futures_positions,
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
        unprotected_positions=[
            UnprotectedPositionOut(
                bot_id=p.bot_id,
                name=p.name,
                symbol=p.symbol,
                mode=p.mode,
                quantity=p.quantity,
                stop_price=p.stop_price,
            )
            for p in status.unprotected_positions
        ],
        clock=None
        if status.clock is None
        else ClockOut(
            skew_ms=status.clock.skew_ms,
            measured_at=status.clock.measured_at,
            warning=status.clock.warning,
            blocking_live=status.clock.blocking_live,
        ),
        backup=None
        if status.backup is None
        else BackupOut(
            last_backup=_record(status.backup.last_backup),
            last_restore_check=_record(status.backup.last_restore_check),
            overdue=status.backup.overdue,
        ),
    )
