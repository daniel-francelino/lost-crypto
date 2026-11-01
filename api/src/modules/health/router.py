from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Request, Response, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

router = APIRouter(prefix="/health", tags=["health"])


class HealthResponse(BaseModel):
    status: Literal["ok", "unavailable"]
    database: Literal["ok", "unavailable"] | None = None


@router.get("", response_model=HealthResponse)
async def health(request: Request, response: Response) -> HealthResponse:
    """Readiness: the process is up and the database is reachable."""
    engine: AsyncEngine = request.app.state.engine
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthResponse(status="unavailable", database="unavailable")
    return HealthResponse(status="ok", database="ok")


@router.get("/live", response_model=HealthResponse)
async def live() -> HealthResponse:
    """Liveness: the process is running (no dependencies checked)."""
    return HealthResponse(status="ok")


class WorkerHealthResponse(BaseModel):
    status: Literal["ok", "stale"]
    last_heartbeat_at: datetime | None
    age_seconds: float | None


@router.get("/worker", response_model=WorkerHealthResponse)
async def worker(request: Request, response: Response) -> WorkerHealthResponse:
    """Is the worker alive? 503 when its heartbeat is older than WORKER_STALE_AFTER_SECONDS.

    For a monitor OUTSIDE this host (book 1 ch. 4, O3): the only way to learn that the whole
    machine is down while nobody has the app open. Unauthenticated and without sensitive data.
    """
    state = await request.app.state.container.status.worker_status()
    if not state.alive:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return WorkerHealthResponse(
        status="ok" if state.alive else "stale",
        last_heartbeat_at=state.last_heartbeat_at,
        age_seconds=state.age_seconds,
    )
