from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import AwareDatetime, BaseModel, Field

from container import Container
from core.jobs import JobStatus
from modules.market_data.application.ports import ImportJob
from modules.market_data.application.service import REFERENCE_SYMBOL, InvalidImportRequest
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
    candles_rejected: int = Field(
        default=0, description="Invalid candles (e.g. high below close) that were not stored."
    )
    candles_changed: int = Field(
        default=0, description="Stored candles the exchange now reports differently (updated)."
    )
    rejection_samples: list[dict[str, Any]] = Field(
        default_factory=list, description="Up to 20 rejected candles with their problem codes."
    )


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


class RangeCoverageOut(BaseModel):
    start: datetime
    end: datetime
    expected: int = Field(description="Closed candles the range should have.")
    present: int
    missing: int
    largest_gap: int = Field(description="Candles missing in the largest single hole.")
    gaps: list[GapOut]


class CoverageOut(BaseModel):
    exchange: str
    symbol: str
    timeframe: Timeframe
    count: int
    first: datetime | None
    last: datetime | None
    gaps: list[GapOut] = Field(description="Gaps of the whole stored series.")
    in_range: RangeCoverageOut | None = Field(
        default=None, description="Gaps inside start/end, when both were given."
    )


class OutlierOut(BaseModel):
    open_time: datetime
    close: Decimal
    return_pct: Decimal
    sigmas: Decimal
    reference_symbol: str | None
    reference_return_pct: Decimal | None = Field(
        description="Same-candle move of the reference pair: if it also moved, it was probably "
        "a market-wide move, not bad data."
    )


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
        candles_rejected=job.candles_rejected,
        candles_changed=job.candles_changed,
        rejection_samples=job.rejection_samples,
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
    request: Request,
    symbol: Symbol,
    timeframe: Timeframe,
    exchange: str = "binance",
    start: AwareDatetime | None = None,
    end: AwareDatetime | None = None,
) -> CoverageOut:
    """What is stored for a series, including detected gaps (and those inside start/end)."""
    container: Container = request.app.state.container
    cov = await container.market_data.coverage(exchange, symbol, timeframe, start, end)
    in_range = None
    if cov.in_range is not None and start is not None and end is not None:
        r = cov.in_range
        in_range = RangeCoverageOut(
            start=start,
            end=end,
            expected=r.expected,
            present=r.present,
            missing=r.missing,
            largest_gap=r.largest_gap,
            gaps=[GapOut(start=g.start, end=g.end, missing=g.missing) for g in r.gaps],
        )
    return CoverageOut(
        exchange=cov.exchange,
        symbol=cov.symbol,
        timeframe=cov.timeframe,
        count=cov.count,
        first=cov.first,
        last=cov.last,
        gaps=[GapOut(start=g.start, end=g.end, missing=g.missing) for g in cov.gaps],
        in_range=in_range,
    )


@router.get("/outliers", response_model=list[OutlierOut])
async def get_outliers(
    request: Request,
    symbol: Symbol,
    timeframe: Timeframe,
    start: AwareDatetime,
    end: AwareDatetime,
    k: Annotated[Decimal, Query(gt=1, le=20)] = Decimal(4),
    exchange: str = "binance",
) -> list[OutlierOut]:
    """Close-to-close moves beyond ``k`` standard deviations (Chan suggests ~4) to review.

    Flags, never deletes: crashes are real. Each one comes with the same-candle move of
    BTC/USDT when stored, as a hint of a market-wide move.
    """
    container: Container = request.app.state.container
    try:
        found = await container.market_data.outliers(exchange, symbol, timeframe, start, end, k)
    except InvalidImportRequest as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    reference = None if symbol == REFERENCE_SYMBOL else REFERENCE_SYMBOL
    return [
        OutlierOut(
            open_time=o.open_time,
            close=o.close,
            return_pct=o.return_pct,
            sigmas=o.sigmas,
            reference_symbol=reference if o.reference_return_pct is not None else None,
            reference_return_pct=o.reference_return_pct,
        )
        for o in found
    ]


class ListingOut(BaseModel):
    exchange: str
    symbol: str
    status: str = Field(description="`active`, `inactive` (listed but halted) or `delisted`.")
    first_seen: datetime = Field(description="First daily snapshot that listed the pair.")
    last_seen: datetime
    delisted_at: datetime | None


@router.get("/listings", response_model=list[ListingOut])
async def get_listings(
    request: Request, exchange: str = "binance", symbol: Symbol | None = None
) -> list[ListingOut]:
    """Pairs the exchange listed, from daily snapshots taken by the worker.

    The history starts on the day the snapshots began: older delistings are unknown.
    """
    container: Container = request.app.state.container
    return [
        ListingOut(
            exchange=item.exchange,
            symbol=item.symbol,
            status=item.status,
            first_seen=item.first_seen,
            last_seen=item.last_seen,
            delisted_at=item.delisted_at,
        )
        for item in await container.market_data.listings(exchange, symbol)
    ]
