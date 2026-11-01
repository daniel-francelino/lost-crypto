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
from modules.analytics.domain.sizing import (
    MIN_KELLY_RETURNS,
    growth_rate,
    half_kelly,
    kelly_fraction,
    suggest_fraction,
    tail_cap,
)
from modules.analytics.presentation.schemas import MetricsOut
from modules.backtesting.application.ports import BacktestRun
from modules.backtesting.application.service import BacktestNotFound
from modules.backtesting.domain.models import BacktestConfig, FillTiming
from modules.backtesting.domain.robustness import assess
from modules.market_data.domain.models import Timeframe
from modules.risk_management.presentation.schemas import RiskLimitsIn
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
    fill_timing: FillTiming = Field(
        default=FillTiming.NEXT_OPEN,
        description=(
            "`next_open`: fill at the next candle's open (default). `signal_close`: fill at the "
            "close of the signal candle, like the bots do (use it to compare with a bot)."
        ),
    )
    risk: RiskLimitsIn | None = Field(
        default=None,
        description=(
            "Size and pause exactly like a bot with these limits (the bot's risk module). "
            "Null keeps the all-in sizing."
        ),
    )
    allow_gaps: bool = Field(
        default=False,
        description=(
            "Run even when the range misses more than 1% of its candles or has a hole longer "
            "than 24 h (otherwise 422). The gaps are reported in `data_quality.gaps`."
        ),
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


class RiskReportOut(BaseModel):
    sizing: str = Field(description="`all_in` or `risk_limits`.")
    paused_at: datetime | None
    paused_reason: str | None
    refusals: dict[str, int] = Field(description="Refused signals by reason.")


class SizingScope(StrEnum):
    DAY = "day"
    BAR = "bar"


class SizingBinding(StrEnum):
    HALF_KELLY = "half_kelly"
    TAIL_STRATEGY = "tail_strategy"
    TAIL_ASSET = "tail_asset"
    SPOT_LIMIT = "spot_limit"


class SizingSampleOut(BaseModel):
    returns: int
    gaps: int
    min_required: int


class KellyOut(BaseModel):
    full: Decimal
    half: Decimal
    growth_full: Decimal
    growth_half: Decimal
    mean: Decimal | None
    variance: Decimal | None


class TailOut(BaseModel):
    strategy_worst_loss_pct: Decimal | None
    asset_worst_loss_pct: Decimal | None
    cap_strategy: Decimal | None
    cap_asset: Decimal | None
    strategy_at: datetime | None
    asset_at: datetime | None


class SizingAdviceOut(BaseModel):
    run_id: UUID
    scope: SizingScope
    tolerable_loss_pct: Decimal
    sample: SizingSampleOut
    kelly: KellyOut | None
    tail: TailOut | None
    configured_fraction: Decimal
    suggested_max_position_fraction: Decimal
    binding: SizingBinding
    above_reference: bool
    warnings: list[str]


class RegimeBandOut(BaseModel):
    label: str
    bars: int
    share_pct: Decimal
    strategy_return_pct: Decimal | None
    asset_return_pct: Decimal | None
    in_market_pct: Decimal | None


class RegimeDimensionOut(BaseModel):
    cut_low: Decimal | None
    cut_high: Decimal | None
    bands: list[RegimeBandOut]


class RegimeOut(BaseModel):
    window: int
    method: str
    volatility: RegimeDimensionOut
    efficiency: RegimeDimensionOut


class GapItemOut(BaseModel):
    start: datetime
    end: datetime
    missing: int


class GapsSummaryOut(BaseModel):
    expected: int
    present: int
    missing: int
    gap_count: int
    largest_gap_candles: int
    largest_gap_seconds: int
    over_limit: bool
    allowed: bool
    gaps: list[GapItemOut] = Field(description="Up to 20 gaps.")


class CandleSampleOut(BaseModel):
    open_time: datetime
    problems: list[str]


class OutlierSampleOut(BaseModel):
    open_time: datetime
    return_pct: Decimal
    sigmas: Decimal


class SampleCheckOut(BaseModel):
    free_parameters: int
    bars: int
    round_trips: int
    min_bars: int = Field(description="252 x free parameters (Chan's rule of thumb).")
    min_round_trips: int
    meets_bar_rule: bool
    meets_trade_rule: bool


class DataQualityOut(BaseModel):
    """What the result rests on. Older runs miss some or all of it."""

    gaps: GapsSummaryOut | None = None
    invalid_candles: int | None = None
    invalid_samples: list[CandleSampleOut] = Field(default_factory=list)
    outlier_sigmas: Decimal | None = None
    outliers: int | None = Field(
        default=None, description="Close-to-close moves beyond outlier_sigmas std. deviations."
    )
    outlier_samples: list[OutlierSampleOut] = Field(default_factory=list)
    sample: SampleCheckOut | None = None


class RobustnessOut(BaseModel):
    verdict: str = Field(description="`plateau`, `peak`, `unprofitable` or `insufficient`.")
    metric: SweepRankBy
    winner_score: Decimal | None
    neighbours: int
    neighbour_mean: Decimal | None
    neighbour_min: Decimal | None
    neighbour_ratio: Decimal | None = Field(description="Neighbour mean / winner score.")
    profitable_share: Decimal | None = Field(description="% of scored combinations above 0.")
    median: Decimal | None
    top3_mean: Decimal | None
    scored: int


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
    allow_gaps: bool
    fill_timing: FillTiming
    risk: RiskLimitsIn | None
    sweep_id: UUID | None
    data_hash: str | None
    candles_count: int | None
    metrics: MetricsOut | None
    segments: SegmentsOut | None
    periods: PeriodsOut | None
    cost_ladder: CostLadderOut | None
    tolerance: ToleranceOut | None
    data_quality: DataQualityOut | None
    risk_report: RiskReportOut | None
    tail_risk: dict[str, Any] | None = None
    regime: RegimeOut | None = None
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
    robustness: RobustnessOut | None
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
        allow_gaps=c.allow_gaps,
        fill_timing=c.fill_timing,
        risk=None if c.risk is None else RiskLimitsIn.from_domain(c.risk),
        sweep_id=run.sweep_id,
        data_hash=run.data_hash,
        candles_count=run.candles_count,
        metrics=MetricsOut.model_validate(run.metrics) if run.metrics else None,
        segments=SegmentsOut.model_validate(run.segments) if run.segments else None,
        periods=PeriodsOut.model_validate(run.periods) if run.periods else None,
        cost_ladder=CostLadderOut.model_validate(run.cost_ladder) if run.cost_ladder else None,
        tolerance=_tolerance(run),
        data_quality=DataQualityOut.model_validate(run.data_quality) if run.data_quality else None,
        risk_report=RiskReportOut.model_validate(run.risk_report) if run.risk_report else None,
        tail_risk=run.tail_risk,
        regime=RegimeOut.model_validate(run.regime) if run.regime else None,
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
        allow_gaps=body.allow_gaps,
        fill_timing=body.fill_timing,
        risk=None if body.risk is None else body.risk.to_domain(),
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


def _robustness(
    grid: dict[str, list[Any]], scored: list[tuple[dict[str, Any], Decimal]], metric: SweepRankBy
) -> RobustnessOut | None:
    if not scored:
        return None
    r = assess(grid, scored)
    return RobustnessOut(
        verdict=r.verdict.value,
        metric=metric,
        winner_score=r.winner_score,
        neighbours=r.neighbours,
        neighbour_mean=r.neighbour_mean,
        neighbour_min=r.neighbour_min,
        neighbour_ratio=r.neighbour_ratio,
        profitable_share=r.profitable_share,
        median=r.median,
        top3_mean=r.top3_mean,
        scored=r.scored,
    )


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
    scored = [
        (row.strategy_params, value)
        for row in rows
        if row.status is JobStatus.COMPLETED and (value := getattr(row, rank_by.value)) is not None
    ]
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
        robustness=_robustness(sweep.grid, scored, rank_by),
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


@router.get("/{run_id}/sizing", response_model=SizingAdviceOut)
async def get_sizing_advice(
    run_id: UUID,
    request: Request,
    tolerable_loss_pct: Annotated[Decimal, Query(gt=0, le=100)] = Decimal("10"),
    scope: SizingScope = SizingScope.DAY,
) -> dict[str, Any]:
    container: Container = request.app.state.container
    try:
        run = await container.backtests.get(run_id)
    except BacktestNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "backtest not found") from exc
    if run.status is not JobStatus.COMPLETED or run.tail_risk is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "run the backtest again to calculate sizing advice"
        )
    raw = run.tail_risk
    series = raw["strategy"]
    asset = raw["asset"]
    inputs = raw["kelly_inputs"]
    count = int(inputs["returns"])
    mean = _decimal(inputs.get("mean"))
    variance = _decimal(inputs.get("variance"))
    full = (
        None
        if count < MIN_KELLY_RETURNS
        else Decimal(0)
        if mean is not None and mean <= 0
        else kelly_fraction(mean, variance)
        if mean is not None and variance is not None
        else None
    )
    half = half_kelly(full) if full is not None else None
    is_day = scope is SizingScope.DAY
    strategy_loss = _decimal(series.get("worst_day_loss_pct" if is_day else "worst_bar_loss_pct"))
    asset_return = _decimal(asset.get("worst_day_return_pct" if is_day else "worst_bar_return_pct"))
    asset_loss = -asset_return if asset_return is not None and asset_return < 0 else None
    cap_strategy = tail_cap(tolerable_loss_pct, strategy_loss)
    cap_asset = tail_cap(tolerable_loss_pct, asset_loss)
    configured = run.config.risk.max_position_fraction if run.config.risk else Decimal(1)
    advice = suggest_fraction(
        configured, half, [("tail_strategy", cap_strategy), ("tail_asset", cap_asset)]
    )
    warnings = [
        "Kelly pressupõe retornos estáveis e aproximadamente gaussianos; cripto tem caudas gordas.",
        "Estimativas dentro da amostra compartilham o viés de sobreajuste do backtest.",
        "Esta sugestão é consultiva e não altera o tamanho das ordens.",
    ]
    if count < MIN_KELLY_RETURNS:
        warnings.append(
            f"Amostra insuficiente para Kelly: são necessários {MIN_KELLY_RETURNS} retornos."
        )
    if mean is not None and mean <= 0:
        warnings.append("A simulação não mostrou vantagem positiva.")
    if run.config.risk and run.config.risk.max_risk_per_trade_pct is not None:
        warnings.append("O risco por operação limita ainda mais a exposição efetiva configurada.")
    tail = (
        None
        if strategy_loss is None and asset_loss is None
        else {
            "strategy_worst_loss_pct": strategy_loss,
            "asset_worst_loss_pct": asset_loss,
            "cap_strategy": cap_strategy,
            "cap_asset": cap_asset,
            "strategy_at": series.get("worst_day_at" if is_day else "worst_bar_at"),
            "asset_at": asset.get("worst_day_at" if is_day else "worst_bar_at"),
        }
    )
    return {
        "run_id": run_id,
        "scope": scope,
        "tolerable_loss_pct": tolerable_loss_pct,
        "sample": {
            "returns": count,
            "gaps": int(inputs["gaps"]),
            "min_required": MIN_KELLY_RETURNS,
        },
        "kelly": None
        if full is None
        else {
            "full": full,
            "half": half,
            "growth_full": growth_rate(full, mean or Decimal(0), variance or Decimal(0)),
            "growth_half": growth_rate(
                half or Decimal(0), mean or Decimal(0), variance or Decimal(0)
            ),
            "mean": mean,
            "variance": variance,
        },
        "tail": tail,
        "configured_fraction": configured,
        "suggested_max_position_fraction": advice.value,
        "binding": SizingBinding(advice.binding),
        "above_reference": half is not None and configured > advice.value,
        "warnings": warnings,
    }


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
