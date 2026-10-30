from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import AwareDatetime, BaseModel, Field

from container import Container
from core.jobs import JobStatus
from modules.market_data.application.ports import ImportJob
from modules.market_data.application.service import InvalidImportRequest
from modules.market_data.domain.models import Timeframe

router = APIRouter(prefix="/market-data", tags=["market-data"])

Symbol = Annotated[str, Field(pattern=r"^[A-Z0-9]{2,15}/[A-Z0-9]{2,15}$", examples=["BTC/USDT"])]


class ImportRequest(BaseModel):
    exchange: str = "binance"
    symbol: Symbol = "BTC/USDT"
    timeframe: Timeframe = Timeframe.H1
    start: AwareDatetime = Field(description="Inclusive, timezone-aware (UTC recommended)")
    end: AwareDatetime = Field(description="Exclusive. Candles still in progress are skipped")


class ImportJobOut(BaseModel):
    id: UUID
    exchange: str
    symbol: str
    timeframe: Timeframe
    start: datetime
    end: datetime
    status: JobStatus
    candles_imported: int
    error: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class CandleOut(BaseModel):
    open_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal


class GapOut(BaseModel):
    start: datetime
    end: datetime
    missing: int


class CoverageOut(BaseModel):
    exchange: str
    symbol: str
    timeframe: Timeframe
    count: int
    first: datetime | None
    last: datetime | None
    gaps: list[GapOut]


def _job_out(job: ImportJob) -> ImportJobOut:
    return ImportJobOut(
        id=job.id,
        exchange=job.exchange,
        symbol=job.symbol,
        timeframe=job.timeframe,
        start=job.start,
        end=job.end,
        status=job.status,
        candles_imported=job.candles_imported,
        error=job.error,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
    )


@router.post("/imports", response_model=ImportJobOut, status_code=status.HTTP_202_ACCEPTED)
async def request_import(body: ImportRequest, request: Request) -> ImportJobOut:
    """Queue a historical candle import. The worker runs it; poll the job for progress."""
    container: Container = request.app.state.container
    try:
        job = await container.market_data.request_import(
            body.exchange, body.symbol, body.timeframe, body.start, body.end
        )
    except InvalidImportRequest as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    return _job_out(job)


@router.get("/imports", response_model=list[ImportJobOut])
async def list_imports(
    request: Request, limit: Annotated[int, Query(ge=1, le=200)] = 50
) -> list[ImportJobOut]:
    container: Container = request.app.state.container
    return [_job_out(j) for j in await container.market_data.list_imports(limit)]


@router.get("/imports/{job_id}", response_model=ImportJobOut)
async def get_import(job_id: UUID, request: Request) -> ImportJobOut:
    container: Container = request.app.state.container
    job = await container.market_data.get_import(job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "import job not found")
    return _job_out(job)


@router.get("/candles", response_model=list[CandleOut])
async def get_candles(
    request: Request,
    symbol: Symbol,
    timeframe: Timeframe,
    start: AwareDatetime,
    end: AwareDatetime,
    limit: Annotated[int, Query(ge=1, le=5000)] = 1000,
    exchange: str = "binance",
) -> list[CandleOut]:
    """Stored candles with ``start <= open_time < end`` (at most ``limit``, oldest first)."""
    container: Container = request.app.state.container
    candles = await container.market_data.candles(exchange, symbol, timeframe, start, end)
    return [
        CandleOut(
            open_time=c.open_time,
            open=c.open,
            high=c.high,
            low=c.low,
            close=c.close,
            volume=c.volume,
        )
        for c in candles[:limit]
    ]


@router.get("/coverage", response_model=CoverageOut)
async def get_coverage(
    request: Request, symbol: Symbol, timeframe: Timeframe, exchange: str = "binance"
) -> CoverageOut:
    """What is stored for a series, including detected gaps."""
    container: Container = request.app.state.container
    cov = await container.market_data.coverage(exchange, symbol, timeframe)
    return CoverageOut(
        exchange=cov.exchange,
        symbol=cov.symbol,
        timeframe=cov.timeframe,
        count=cov.count,
        first=cov.first,
        last=cov.last,
        gaps=[GapOut(start=g.start, end=g.end, missing=g.missing) for g in cov.gaps],
    )
