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
