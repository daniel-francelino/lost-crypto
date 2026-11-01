from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import AwareDatetime, BaseModel, Field

from container import Container
from core.jobs import JobStatus
from core.security.auth import Principal, require_auth
from modules.analytics.domain.mean_reversion import suggested_windows
from modules.market_data.application.ports import ImportJob
from modules.market_data.application.service import REFERENCE_SYMBOL, InvalidImportRequest
from modules.market_data.domain.models import RegimeBreak, Timeframe
from modules.market_data.domain.pairs import SUPPORTED_PAIRS

router = APIRouter(prefix="/market-data", tags=["market-data"])

Symbol = Annotated[str, Field(pattern=r"^[A-Z0-9]{2,15}/USDT$", examples=["BTC/USDT"])]


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


class VarianceRatioOut(BaseModel):
    lag: int
    ratio: Decimal
    z_stat: Decimal


class HalfLifeOut(BaseModel):
    n: int
    slope: Decimal | None
    t_stat: Decimal | None
    stationary_at_5pct: bool | None
    half_life_bars: Decimal | None
    half_life_seconds: Decimal | None
    log_prices: bool
    gaps: int
    warning: str
    sample_every: int = Field(
        default=1, description="One close per this many candles (1 = every candle)."
    )
    hurst: Decimal | None = Field(
        default=None,
        description="Hurst exponent by the variance-of-differences method: below 0.5 reverts, "
        "0.5 is a random walk, above 0.5 trends. Null on a short series.",
    )
    suggested_windows: list[int] = Field(
        default_factory=list,
        description="Look-back windows around the half-life (0.5x, 1x, 2x), in the sampled "
        "bars; empty unless the series looks stationary at 5%. A search range, not advice.",
    )
    variance_ratios: list[VarianceRatioOut] = Field(
        default_factory=list,
        description="Variance ratio per lag: below 1 reverts, 1 random walk, above 1 trends. "
        "z_stat assumes constant volatility, which crypto does not have.",
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


class SupportedPairOut(BaseModel):
    symbol: str
    base: str
    quote: str
    name: str


@router.get("/symbols", response_model=list[SupportedPairOut])
async def list_symbols() -> list[SupportedPairOut]:
    """The USDT pairs offered in the selectors (the quote is always USDT)."""
    return [
        SupportedPairOut(symbol=p.symbol, base=p.base, quote="USDT", name=p.name)
        for p in SUPPORTED_PAIRS
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


@router.get("/half-life", response_model=HalfLifeOut)
async def get_half_life(
    request: Request,
    symbol: Symbol,
    timeframe: Timeframe,
    start: AwareDatetime,
    end: AwareDatetime,
    log_prices: bool = True,
    sample_every: Annotated[int, Query(ge=1, le=1000)] = 1,
    exchange: str = "binance",
) -> HalfLifeOut:
    """Estimate mean-reversion half-life from stored close prices; descriptive only."""
    if start >= end:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "start must be before end")
    container: Container = request.app.state.container
    try:
        diagnostics, n, gaps = await container.market_data.half_life(
            exchange, symbol, timeframe, start, end, log=log_prices, sample_every=sample_every
        )
        estimate = diagnostics.half_life
    except InvalidImportRequest as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    return HalfLifeOut(
        n=n,
        slope=None if estimate is None else estimate.slope,
        t_stat=None if estimate is None else estimate.t_stat,
        stationary_at_5pct=None if estimate is None else estimate.stationary,
        half_life_bars=None if estimate is None else estimate.half_life_bars,
        half_life_seconds=(
            None
            if estimate is None
            else estimate.half_life_bars * int(timeframe.delta.total_seconds())
        ),
        log_prices=log_prices,
        gaps=gaps,
        sample_every=sample_every,
        hurst=diagnostics.hurst,
        suggested_windows=(
            suggested_windows(estimate.half_life_bars)
            if estimate is not None and estimate.stationary
            else []
        ),
        variance_ratios=[
            VarianceRatioOut(lag=r.lag, ratio=r.ratio, z_stat=r.z_stat)
            for r in diagnostics.variance_ratios
        ],
        warning=(
            "Estimativa descritiva, não é previsão. A meia-vida só é interpretável quando "
            "a série é estacionária; dados com lacunas foram usados como estão."
        ),
    )


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


class RegimeBreakIn(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=60)]
    occurred_at: AwareDatetime
    exchange: str | None = Field(default=None, description="Null: applies to every exchange.")
    symbol: Symbol | None = Field(default=None, description="Null: applies to every symbol.")
    note: Annotated[str, Field(max_length=500)] | None = None


class RegimeBreakOut(BaseModel):
    id: UUID
    name: str
    occurred_at: datetime
    exchange: str | None
    symbol: str | None
    note: str | None
    created_by: str
    created_at: datetime


def _break_out(b: RegimeBreak) -> RegimeBreakOut:
    return RegimeBreakOut(
        id=b.id,
        name=b.name,
        occurred_at=b.occurred_at,
        exchange=b.exchange,
        symbol=b.symbol,
        note=b.note,
        created_by=b.created_by,
        created_at=b.created_at,
    )


@router.get("/regime-breaks", response_model=list[RegimeBreakOut])
async def list_regime_breaks(
    request: Request, exchange: str | None = None, symbol: Symbol | None = None
) -> list[RegimeBreakOut]:
    """Structural breaks the operator named (global ones included when a market is given)."""
    container: Container = request.app.state.container
    return [_break_out(b) for b in await container.market_data.list_breaks(exchange, symbol)]


@router.post("/regime-breaks", response_model=RegimeBreakOut, status_code=status.HTTP_201_CREATED)
async def create_regime_break(
    body: RegimeBreakIn, request: Request, principal: Principal = Depends(require_auth)
) -> RegimeBreakOut:
    """Name a break (a crash, a rule change). Register breaks BEFORE running experiments: each one
    keeps when it was created, and a break chosen after seeing results is a research freedom."""
    container: Container = request.app.state.container
    created = await container.market_data.create_break(
        body.name, body.occurred_at, body.exchange, body.symbol, body.note, principal.username
    )
    await container.audit.record(
        "regime_break.created",
        "regime_break",
        str(created.id),
        principal.username,
        {"name": created.name, "occurred_at": created.occurred_at.isoformat()},
    )
    return _break_out(created)


@router.delete("/regime-breaks/{break_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_regime_break(
    break_id: UUID, request: Request, principal: Principal = Depends(require_auth)
) -> Response:
    """Breaks are never edited: delete and create again, which leaves a trail."""
    container: Container = request.app.state.container
    await container.market_data.delete_break(break_id)
    await container.audit.record(
        "regime_break.deleted", "regime_break", str(break_id), principal.username, {}
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


class GridCellOut(BaseModel):
    lookback: int
    holding: int
    n: int = Field(description="Independent (non-overlapping) samples behind the correlation.")
    correlation: Decimal | None
    z_stat: Decimal | None
    significant_corrected: bool | None = Field(
        description="|z| reaches the Bonferroni-corrected level of the whole grid."
    )
    reason: str | None


class MomentumGridOut(BaseModel):
    cells: list[GridCellOut]
    alpha_corrected: Decimal = Field(description="0.05 divided by the number of cells.")
    critical_z: Decimal
    candles: int
    gaps: int
    warning: str


def _parse_lags(text: str, name: str) -> list[int]:
    try:
        values = [int(part) for part in text.split(",") if part.strip() != ""]
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"{name}: use integers") from exc
    if not values:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"{name}: give at least one")
    return values


@router.get("/momentum-grid", response_model=MomentumGridOut)
async def get_momentum_grid(
    request: Request,
    symbol: Symbol,
    timeframe: Timeframe,
    start: AwareDatetime,
    end: AwareDatetime,
    lookbacks: Annotated[str, Query(max_length=100)] = "1,5,10,25",
    holdings: Annotated[str, Query(max_length=100)] = "1,5,10,25",
    exchange: str = "binance",
) -> MomentumGridOut:
    """Correlation between the return over ``lookback`` candles and the next ``holding`` candles,
    with non-overlapping samples. Descriptive: a grid is many tests, so significance is against
    the corrected level; correlation is not profit."""
    if start >= end:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "start must be before end")
    container: Container = request.app.state.container
    try:
        cells, alpha, critical, candles, gaps = await container.market_data.momentum_grid(
            exchange,
            symbol,
            timeframe,
            start,
            end,
            _parse_lags(lookbacks, "lookbacks"),
            _parse_lags(holdings, "holdings"),
        )
    except InvalidImportRequest as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    return MomentumGridOut(
        cells=[
            GridCellOut(
                lookback=c.lookback,
                holding=c.holding,
                n=c.n,
                correlation=c.correlation,
                z_stat=c.z_stat,
                significant_corrected=c.significant_corrected,
                reason=c.reason,
            )
            for c in cells
        ],
        alpha_corrected=alpha,
        critical_z=critical,
        candles=candles,
        gaps=gaps,
        warning=(
            "Descritivo. Uma grade são muitos testes: use o nível corrigido, não escolha a "
            "melhor célula. Correlação não paga custos e não é lucro negociável."
        ),
    )
