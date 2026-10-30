from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import AwareDatetime, BaseModel, Field

from container import Container
from core.errors import DomainError
from core.jobs import JobStatus
from modules.analytics.presentation.schemas import MetricsOut
from modules.backtesting.application.ports import BacktestRun
from modules.backtesting.application.service import BacktestNotFound
from modules.backtesting.domain.models import BacktestConfig
from modules.market_data.domain.models import Timeframe
from modules.strategies.domain.types import Side

router = APIRouter(prefix="/backtests", tags=["backtests"])

Symbol = Annotated[str, Field(pattern=r"^[A-Z0-9]{2,15}/[A-Z0-9]{2,15}$")]


class BacktestCreate(BaseModel):
    exchange: str = "binance"
    strategy_type: str = Field(examples=["ema_crossover"])
    strategy_params: dict[str, Any] = Field(
        default_factory=dict, examples=[{"fast_period": 9, "slow_period": 21}]
    )
    symbol: Symbol = "BTC/USDT"
    timeframe: Timeframe = Timeframe.H1
    start: AwareDatetime
    end: AwareDatetime
    initial_capital: Decimal = Field(default=Decimal("1000"), gt=0)
    fee_rate: Decimal | None = Field(
        default=None,
        ge=0,
        lt=1,
        description="Fraction of notional (0.001 = 0.1%). Defaults to the exchange's taker fee.",
    )
    slippage_bps: Decimal = Field(
        default=Decimal("5"), ge=0, lt=10000, description="Adverse slippage per fill, in bps"
    )
    seed: int = 0
    test_fraction: Decimal | None = Field(
        default=None,
        gt=0,
        lt=1,
        description=(
            "Hold out this share of the series (at the end) as an out-of-sample test part. "
            "Train and test metrics are then reported separately in `segments`."
        ),
    )


class SweepCreate(BacktestCreate):
    grid: dict[str, list[Any]] = Field(
        min_length=1,
        description="Parameter name -> values to try. One run per combination (max 200).",
        examples=[{"fast_period": [5, 9, 12], "slow_period": [21, 50]}],
    )


class SegmentsOut(BaseModel):
    split_at: datetime
    test_fraction: Decimal
    train: MetricsOut
    test: MetricsOut


class BacktestOut(BaseModel):
    id: UUID
    status: JobStatus
    strategy_type: str
    strategy_params: dict[str, Any]
    exchange: str
    symbol: str
    timeframe: Timeframe
    start: datetime
    end: datetime
    initial_capital: Decimal
    fee_rate: Decimal
    slippage_bps: Decimal
    seed: int
    test_fraction: Decimal | None
    sweep_id: UUID | None
    data_hash: str | None
    candles_count: int | None
    metrics: MetricsOut | None
    segments: SegmentsOut | None
    error: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class SweepRunOut(BaseModel):
    id: UUID
    status: JobStatus
    strategy_params: dict[str, Any]
    total_return_pct: Decimal | None
    test_return_pct: Decimal | None
    max_drawdown_pct: Decimal | None
    round_trips: int | None
    buy_and_hold_return_pct: Decimal | None
    error: str | None


class SweepOut(BaseModel):
    id: UUID
    created_at: datetime
    strategy_type: str
    grid: dict[str, list[Any]]
    run_count: int
    completed: int
    failed: int
    skipped: list[dict[str, Any]]
    ranked_by: str
    note: str
    runs: list[SweepRunOut]


class TradeOut(BaseModel):
    time: datetime
    side: Side
    quantity: Decimal
    price: Decimal
    fee: Decimal
    notional: Decimal


class EquityPointOut(BaseModel):
    time: datetime
    equity: Decimal


def _out(run: BacktestRun) -> BacktestOut:
    c = run.config
    return BacktestOut(
        id=run.id,
        status=run.status,
        strategy_type=c.strategy_type,
        strategy_params=dict(c.strategy_params),
        exchange=c.exchange,
        symbol=c.symbol,
        timeframe=c.timeframe,
        start=c.start,
        end=c.end,
        initial_capital=c.initial_capital,
        fee_rate=c.fee_rate,
        slippage_bps=c.slippage_bps,
        seed=c.seed,
        test_fraction=c.test_fraction,
        sweep_id=run.sweep_id,
        data_hash=run.data_hash,
        candles_count=run.candles_count,
        metrics=MetricsOut.model_validate(run.metrics) if run.metrics else None,
        segments=SegmentsOut.model_validate(run.segments) if run.segments else None,
        error=run.error,
        created_at=run.created_at,
        started_at=run.started_at,
        finished_at=run.finished_at,
    )


def _config(body: BacktestCreate, container: Container) -> BacktestConfig:
    return BacktestConfig(
        exchange=body.exchange,
        symbol=body.symbol,
        timeframe=body.timeframe,
        start=body.start,
        end=body.end,
        initial_capital=body.initial_capital,
        fee_rate=(
            body.fee_rate
            if body.fee_rate is not None
            else container.exchanges.profile(body.exchange).fees.taker_rate
        ),
        slippage_bps=body.slippage_bps,
        strategy_type=body.strategy_type,
        strategy_params=body.strategy_params,
        seed=body.seed,
        test_fraction=body.test_fraction,
    )


def _decimal(value: object) -> Decimal | None:
    return None if value is None else Decimal(str(value))


def _sweep_run(run: BacktestRun) -> SweepRunOut:
    metrics = run.metrics or {}
    test = (run.segments or {}).get("test") or {}
    return SweepRunOut(
        id=run.id,
        status=run.status,
        strategy_params=dict(run.config.strategy_params),
        total_return_pct=_decimal(metrics.get("total_return_pct")),
        test_return_pct=_decimal(test.get("total_return_pct")),
        max_drawdown_pct=_decimal(metrics.get("max_drawdown_pct")),
        round_trips=metrics.get("round_trips"),
        buy_and_hold_return_pct=_decimal(metrics.get("buy_and_hold_return_pct")),
        error=run.error,
    )


@router.post("", response_model=BacktestOut, status_code=status.HTTP_202_ACCEPTED)
async def create_backtest(body: BacktestCreate, request: Request) -> BacktestOut:
    """Queue a backtest. The worker executes it; poll ``GET /backtests/{id}`` for the result.

    Results are simulations on historical data, not a forecast of future returns.
    """
    container: Container = request.app.state.container
    try:
        run = await container.backtests.create(_config(body, container))
    except DomainError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    return _out(run)


@router.post("/sweeps", response_model=SweepOut, status_code=status.HTTP_202_ACCEPTED)
async def create_sweep(body: SweepCreate, request: Request) -> SweepOut:
    """Queue one backtest per parameter combination of ``grid`` and compare them.

    Combinations the strategy rejects (e.g. fast >= slow) are skipped and reported. With
    ``test_fraction`` set, rank by the test (out-of-sample) return to avoid picking an overfit
    parameter set.
    """
    container: Container = request.app.state.container
    try:
        sweep, runs = await container.backtests.create_sweep(_config(body, container), body.grid)
    except DomainError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    return _sweep_out(sweep, runs)


def _sweep_out(sweep: Any, runs: list[BacktestRun]) -> SweepOut:
    use_test = bool(runs) and runs[0].config.test_fraction is not None
    rows = [_sweep_run(r) for r in runs]

    def score(row: SweepRunOut) -> Decimal:
        value = row.test_return_pct if use_test else row.total_return_pct
        return value if value is not None else Decimal("-Infinity")

    rows.sort(key=score, reverse=True)
    return SweepOut(
        id=sweep.id,
        created_at=sweep.created_at,
        strategy_type=sweep.strategy_type,
        grid=sweep.grid,
        run_count=sweep.run_count,
        completed=sum(1 for r in runs if r.status is JobStatus.COMPLETED),
        failed=sum(1 for r in runs if r.status is JobStatus.FAILED),
        skipped=sweep.skipped,
        ranked_by="test_return_pct" if use_test else "total_return_pct",
        note=(
            "Ranked by out-of-sample (test) return."
            if use_test
            else "Ranked by full-period return, which favours overfit parameters: "
            "use test_fraction to rank out-of-sample."
        ),
        runs=rows,
    )


@router.get("", response_model=list[BacktestOut])
async def list_backtests(
    request: Request, limit: Annotated[int, Query(ge=1, le=200)] = 50
) -> list[BacktestOut]:
    container: Container = request.app.state.container
    return [_out(r) for r in await container.backtests.list_runs(limit)]


@router.get("/compare", response_model=list[BacktestOut])
async def compare_backtests(
    request: Request, ids: Annotated[list[UUID], Query(min_length=2, max_length=10)]
) -> list[BacktestOut]:
    """Several backtests side by side, in the order requested."""
    container: Container = request.app.state.container
    return [_out(await container.backtests.get(run_id)) for run_id in ids]


@router.get("/sweeps/{sweep_id}", response_model=SweepOut)
async def get_sweep(sweep_id: UUID, request: Request) -> SweepOut:
    container: Container = request.app.state.container
    sweep, runs = await container.backtests.get_sweep(sweep_id)
    return _sweep_out(sweep, runs)


@router.get("/{run_id}", response_model=BacktestOut)
async def get_backtest(run_id: UUID, request: Request) -> BacktestOut:
    container: Container = request.app.state.container
    try:
        return _out(await container.backtests.get(run_id))
    except BacktestNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "backtest not found") from exc


@router.get("/{run_id}/trades", response_model=list[TradeOut])
async def get_trades(run_id: UUID, request: Request) -> list[TradeOut]:
    """Simulated fills (buys and sells) in chronological order."""
    container: Container = request.app.state.container
    try:
        fills = await container.backtests.trades(run_id)
    except BacktestNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "backtest not found") from exc
    return [
        TradeOut(
            time=f.time,
            side=f.side,
            quantity=f.quantity,
            price=f.price,
            fee=f.fee,
            notional=f.notional,
        )
        for f in fills
    ]


@router.get("/{run_id}/equity", response_model=list[EquityPointOut])
async def get_equity(run_id: UUID, request: Request) -> list[EquityPointOut]:
    """Equity curve marked at every candle close (empty until the run completes)."""
    container: Container = request.app.state.container
    try:
        curve = await container.backtests.equity_curve(run_id)
    except BacktestNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "backtest not found") from exc
    return [EquityPointOut(time=p.time, equity=p.equity) for p in curve]
