from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import AwareDatetime, BaseModel, Field

from container import EXCHANGE, Container
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
    strategy_type: str = Field(examples=["ema_crossover"])
    strategy_params: dict[str, Any] = Field(
        default_factory=dict, examples=[{"fast_period": 9, "slow_period": 21}]
    )
    symbol: Symbol = "BTC/USDT"
    timeframe: Timeframe = Timeframe.H1
    start: AwareDatetime
    end: AwareDatetime
    initial_capital: Decimal = Field(default=Decimal("1000"), gt=0)
    fee_rate: Decimal = Field(
        default=Decimal("0.001"), ge=0, lt=1, description="Fraction of notional (0.001 = 0.1%)"
    )
    slippage_bps: Decimal = Field(
        default=Decimal("5"), ge=0, lt=10000, description="Adverse slippage per fill, in bps"
    )
    seed: int = 0


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
    data_hash: str | None
    candles_count: int | None
    metrics: MetricsOut | None
    error: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


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
        data_hash=run.data_hash,
        candles_count=run.candles_count,
        metrics=MetricsOut.model_validate(run.metrics) if run.metrics else None,
        error=run.error,
        created_at=run.created_at,
        started_at=run.started_at,
        finished_at=run.finished_at,
    )


@router.post("", response_model=BacktestOut, status_code=status.HTTP_202_ACCEPTED)
async def create_backtest(body: BacktestCreate, request: Request) -> BacktestOut:
    """Queue a backtest. The worker executes it; poll ``GET /backtests/{id}`` for the result.

    Results are simulations on historical data, not a forecast of future returns.
    """
    container: Container = request.app.state.container
    try:
        config = BacktestConfig(
            exchange=EXCHANGE,
            symbol=body.symbol,
            timeframe=body.timeframe,
            start=body.start,
            end=body.end,
            initial_capital=body.initial_capital,
            fee_rate=body.fee_rate,
            slippage_bps=body.slippage_bps,
            strategy_type=body.strategy_type,
            strategy_params=body.strategy_params,
            seed=body.seed,
        )
        run = await container.backtests.create(config)
    except DomainError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    return _out(run)


@router.get("", response_model=list[BacktestOut])
async def list_backtests(
    request: Request, limit: Annotated[int, Query(ge=1, le=200)] = 50
) -> list[BacktestOut]:
    container: Container = request.app.state.container
    return [_out(r) for r in await container.backtests.list_runs(limit)]


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
