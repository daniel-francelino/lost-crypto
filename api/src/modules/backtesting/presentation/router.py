from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from pydantic import AwareDatetime, BaseModel, Field

from container import Container
from core.errors import DomainError
from core.jobs import JobStatus
from core.pagination import Offset, set_total
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
    cost_sensitivity: bool = Field(
        default=False,
        description=(
            "Also re-run the backtest with fee and slippage scaled by 0, 0.5, 1, 1.5, 2 and 3 "
            "and report the break-even cost in `cost_ladder`. Slower; limited to 50,000 candles."
        ),
    )
    max_drawdown_tolerance_pct: Decimal | None = Field(
        default=None,
        gt=0,
        le=100,
        description="Deepest drawdown the operator accepts; `tolerance` flags runs beyond it.",
    )
    max_drawdown_tolerance_days: int | None = Field(
        default=None,
        gt=0,
        le=3650,
        description="Longest drawdown (days below the peak) the operator accepts.",
    )


class SweepCreate(BacktestCreate):
    grid: dict[str, list[Any]] = Field(
        min_length=1,
        description="Parameter name -> values to try. One run per combination (max 200).",
        examples=[{"fast_period": [5, 9, 12], "slow_period": [21, 50]}],
    )


class SweepRankBy(StrEnum):
    TOTAL_RETURN = "total_return_pct"
    TRAIN_RETURN = "train_return_pct"
    TEST_RETURN = "test_return_pct"
    SHARPE = "sharpe_ratio"
    TRAIN_SHARPE = "train_sharpe_ratio"
    TEST_SHARPE = "test_sharpe_ratio"


_NEEDS_SPLIT = {
    SweepRankBy.TRAIN_RETURN,
    SweepRankBy.TEST_RETURN,
    SweepRankBy.TRAIN_SHARPE,
    SweepRankBy.TEST_SHARPE,
}


class PeriodOut(BaseModel):
    label: str
    start: datetime
    end: datetime
    candles: int
    metrics: MetricsOut


class PeriodsOut(BaseModel):
    granularity: str = Field(description="`year`, or `quarter` when the run spans < 2 years.")
    periods: list[PeriodOut]


class CostLevelOut(BaseModel):
    multiplier: Decimal
    fee_rate: Decimal
    slippage_bps: Decimal
    cost_per_side_bps: Decimal
    net_pnl: Decimal
    total_return_pct: Decimal
    sharpe_ratio: Decimal | None
    round_trips: int
    fees_paid: Decimal


class CostLadderOut(BaseModel):
    levels: list[CostLevelOut]
    break_even_status: str = Field(description="`found`, `never_profitable` or `above_max`.")
    break_even_multiplier: Decimal | None
    break_even_cost_per_side_bps: Decimal | None
    note: str


class ToleranceOut(BaseModel):
    max_drawdown_pct: Decimal | None
    max_drawdown_days: int | None
    exceeded_depth: bool | None
    exceeded_duration: bool | None = Field(
        description="Null when the run predates drawdown duration (not computed)."
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
    cost_sensitivity: bool
    max_drawdown_tolerance_pct: Decimal | None
    max_drawdown_tolerance_days: int | None
    sweep_id: UUID | None
    data_hash: str | None
    candles_count: int | None
    metrics: MetricsOut | None
    segments: SegmentsOut | None
    periods: PeriodsOut | None
    cost_ladder: CostLadderOut | None
    tolerance: ToleranceOut | None
    error: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class SweepRunOut(BaseModel):
    id: UUID
    status: JobStatus
    strategy_params: dict[str, Any]
    total_return_pct: Decimal | None = Field(description="Whole period (train + test).")
    train_return_pct: Decimal | None
    test_return_pct: Decimal | None
    sharpe_ratio: Decimal | None
    train_sharpe_ratio: Decimal | None
    test_sharpe_ratio: Decimal | None
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
    trials: int = Field(description="Parameter combinations tried, including skipped ones.")
    prior_trials: int = Field(
        description=(
            "Approximate: earlier completed runs of the same strategy on overlapping data "
            "(same exchange, symbol and timeframe) outside this sweep."
        )
    )
    ranked_by: SweepRankBy
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
        cost_sensitivity=c.cost_sensitivity,
        max_drawdown_tolerance_pct=c.max_drawdown_tolerance_pct,
        max_drawdown_tolerance_days=c.max_drawdown_tolerance_days,
        sweep_id=run.sweep_id,
        data_hash=run.data_hash,
        candles_count=run.candles_count,
        metrics=MetricsOut.model_validate(run.metrics) if run.metrics else None,
        segments=SegmentsOut.model_validate(run.segments) if run.segments else None,
        periods=PeriodsOut.model_validate(run.periods) if run.periods else None,
        cost_ladder=CostLadderOut.model_validate(run.cost_ladder) if run.cost_ladder else None,
        tolerance=_tolerance(run),
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
        cost_sensitivity=body.cost_sensitivity,
        max_drawdown_tolerance_pct=body.max_drawdown_tolerance_pct,
        max_drawdown_tolerance_days=body.max_drawdown_tolerance_days,
    )


def _tolerance(run: BacktestRun) -> ToleranceOut | None:
    """Compares the stored metrics with the operator's tolerance; computed on read."""
    c = run.config
    if c.max_drawdown_tolerance_pct is None and c.max_drawdown_tolerance_days is None:
        return None
    metrics = run.metrics or {}
    depth = _decimal(metrics.get("max_drawdown_pct"))
    seconds = metrics.get("max_drawdown_duration_seconds")
    limit_pct, limit_days = c.max_drawdown_tolerance_pct, c.max_drawdown_tolerance_days
    return ToleranceOut(
        max_drawdown_pct=limit_pct,
        max_drawdown_days=limit_days,
        exceeded_depth=None if limit_pct is None or depth is None else depth > limit_pct,
        exceeded_duration=None
        if limit_days is None or seconds is None
        else int(seconds) > limit_days * 86_400,
    )


def _decimal(value: object) -> Decimal | None:
    return None if value is None else Decimal(str(value))


def _sweep_run(run: BacktestRun) -> SweepRunOut:
    metrics = run.metrics or {}
    train = (run.segments or {}).get("train") or {}
    test = (run.segments or {}).get("test") or {}
    return SweepRunOut(
        id=run.id,
        status=run.status,
        strategy_params=dict(run.config.strategy_params),
        total_return_pct=_decimal(metrics.get("total_return_pct")),
        train_return_pct=_decimal(train.get("total_return_pct")),
        test_return_pct=_decimal(test.get("total_return_pct")),
        sharpe_ratio=_decimal(metrics.get("sharpe_ratio")),
        train_sharpe_ratio=_decimal(train.get("sharpe_ratio")),
        test_sharpe_ratio=_decimal(test.get("sharpe_ratio")),
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


RankBy = Annotated[
    SweepRankBy | None,
    Query(
        description=(
            "Ranking criterion. Default: `train_return_pct` with a train/test split (the test "
            "part then stays a check, not a selection criterion), else `total_return_pct`."
        )
    ),
]


@router.post("/sweeps", response_model=SweepOut, status_code=status.HTTP_202_ACCEPTED)
async def create_sweep(body: SweepCreate, request: Request) -> SweepOut:
    """Queue one backtest per parameter combination of ``grid`` and compare them.

    Combinations the strategy rejects (e.g. fast >= slow) are skipped and reported. With
    ``test_fraction`` set, runs are ranked by the train part and the test part checks the
    winner; choosing by the test part would turn it into selection data.
    """
    container: Container = request.app.state.container
    try:
        sweep, runs, prior = await container.backtests.create_sweep(
            _config(body, container), body.grid
        )
    except DomainError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    return _sweep_out(sweep, runs, prior, None)


_NOTES = {
    SweepRankBy.TOTAL_RETURN: "Ranked by full-period return, which favours overfit parameters: "
    "use test_fraction to rank on the train part and check the winner out of sample.",
    SweepRankBy.SHARPE: "Ranked by full-period Sharpe: the best of many tries is overestimated; "
    "use test_fraction to check the winner out of sample.",
    SweepRankBy.TRAIN_RETURN: "Ranked by train return; the test part is the out-of-sample check "
    "of the winner.",
    SweepRankBy.TRAIN_SHARPE: "Ranked by train Sharpe; the test part is the out-of-sample check "
    "of the winner.",
    SweepRankBy.TEST_RETURN: "Ranked by test return: choosing by the test part uses it up, so it "
    "is no longer out of sample.",
    SweepRankBy.TEST_SHARPE: "Ranked by test Sharpe: choosing by the test part uses it up, so it "
    "is no longer out of sample.",
}


def _sweep_out(
    sweep: Any, runs: list[BacktestRun], prior_trials: int, rank_by: SweepRankBy | None
) -> SweepOut:
    has_split = bool(runs) and runs[0].config.test_fraction is not None
    if rank_by is None:
        rank_by = SweepRankBy.TRAIN_RETURN if has_split else SweepRankBy.TOTAL_RETURN
    elif rank_by in _NEEDS_SPLIT and not has_split:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"ranking by {rank_by.value} needs a sweep created with test_fraction",
        )
    rows = [_sweep_run(r) for r in runs]

    def score(row: SweepRunOut) -> Decimal:
        value: Decimal | None = getattr(row, rank_by.value)
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
        trials=sweep.run_count + len(sweep.skipped),
        prior_trials=prior_trials,
        ranked_by=rank_by,
        note=_NOTES[rank_by],
        runs=rows,
    )


@router.get("", response_model=list[BacktestOut])
async def list_backtests(
    request: Request,
    response: Response,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Offset = 0,
) -> list[BacktestOut]:
    """Newest first; the size of the whole list is in ``X-Total-Count``."""
    container: Container = request.app.state.container
    runs, total = await container.backtests.list_runs(limit, offset)
    set_total(response, total)
    return [_out(r) for r in runs]


@router.get("/compare", response_model=list[BacktestOut])
async def compare_backtests(
    request: Request, ids: Annotated[list[UUID], Query(min_length=2, max_length=10)]
) -> list[BacktestOut]:
    """Several backtests side by side, in the order requested."""
    container: Container = request.app.state.container
    return [_out(await container.backtests.get(run_id)) for run_id in ids]


@router.get("/sweeps/{sweep_id}", response_model=SweepOut)
async def get_sweep(sweep_id: UUID, request: Request, rank_by: RankBy = None) -> SweepOut:
    container: Container = request.app.state.container
    sweep, runs, prior = await container.backtests.get_sweep(sweep_id)
    return _sweep_out(sweep, runs, prior, rank_by)


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
