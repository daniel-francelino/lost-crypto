from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Query, Request, Response, status
from pydantic import BaseModel, Field

from container import Container
from modules.analytics.presentation.schemas import MetricsOut
from modules.bots.domain.models import Bot, BotConfig, BotState, ExecutionMode
from modules.execution.domain.orders import OrderStatus
from modules.market_data.domain.models import Timeframe
from modules.risk_management.domain.models import RiskLimits
from modules.strategies.domain.types import Side, SignalKind

router = APIRouter(prefix="/bots", tags=["bots"])

Symbol = Annotated[str, Field(pattern=r"^[A-Z0-9]{2,15}/[A-Z0-9]{2,15}$")]
Limit = Annotated[int, Query(ge=1, le=500)]


class RiskIn(BaseModel):
    max_position_fraction: Decimal = Field(default=Decimal(1), gt=0, le=1)
    max_order_notional: Decimal | None = Field(default=None, gt=0)
    max_daily_loss_pct: Decimal | None = Field(default=Decimal(10), gt=0, le=100)


class BotCreate(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    strategy_type: str = Field(examples=["ema_crossover"])
    strategy_params: dict[str, Any] = Field(default_factory=dict)
    symbol: Symbol = "BTC/USDT"
    timeframe: Timeframe = Timeframe.H1
    initial_capital: Decimal = Field(default=Decimal(1000), gt=0)
    fee_rate: Decimal = Field(default=Decimal("0.001"), ge=0, lt=1)
    slippage_bps: Decimal = Field(default=Decimal(5), ge=0, lt=10000)
    risk: RiskIn = Field(default_factory=RiskIn)
    mode: Literal["paper"] = "paper"  # testnet/live are not available yet


class BotUpdate(BaseModel):
    """Every field optional. Only allowed while the bot is stopped."""

    name: str | None = Field(default=None, min_length=1, max_length=60)
    strategy_type: str | None = None
    strategy_params: dict[str, Any] | None = None
    symbol: Symbol | None = None
    timeframe: Timeframe | None = None
    initial_capital: Decimal | None = Field(default=None, gt=0)
    fee_rate: Decimal | None = Field(default=None, ge=0, lt=1)
    slippage_bps: Decimal | None = Field(default=None, ge=0, lt=10000)
    risk: RiskIn | None = None


class BotOut(BaseModel):
    id: UUID
    name: str
    strategy_type: str
    strategy_params: dict[str, Any]
    symbol: str
    timeframe: Timeframe
    initial_capital: Decimal
    fee_rate: Decimal
    slippage_bps: Decimal
    risk: RiskIn
    mode: ExecutionMode
    desired_state: BotState
    observed_state: BotState
    config_version: int
    last_heartbeat_at: datetime | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime


class OrderOut(BaseModel):
    id: UUID
    client_order_id: str
    symbol: str
    side: Side
    quantity: Decimal
    status: OrderStatus
    filled_quantity: Decimal
    avg_fill_price: Decimal | None
    reject_reason: str | None
    bar_time: datetime
    created_at: datetime


class SignalOut(BaseModel):
    bar_time: datetime
    side: Side
    kind: SignalKind
    reason: str
    decision: str
    decision_reason: str | None
    created_at: datetime


class PortfolioOut(BaseModel):
    initial_capital: Decimal
    cash: Decimal
    quantity: Decimal
    avg_entry_price: Decimal
    last_price: Decimal | None
    equity: Decimal
    unrealized_pnl: Decimal
    realized_pnl: Decimal
    fees_paid: Decimal


class EquityPointOut(BaseModel):
    time: datetime
    equity: Decimal


def _out(bot: Bot) -> BotOut:
    c = bot.config
    return BotOut(
        id=bot.id,
        name=c.name,
        strategy_type=c.strategy_type,
        strategy_params=dict(c.strategy_params),
        symbol=c.symbol,
        timeframe=c.timeframe,
        initial_capital=c.initial_capital,
        fee_rate=c.fee_rate,
        slippage_bps=c.slippage_bps,
        risk=RiskIn(
            max_position_fraction=c.risk.max_position_fraction,
            max_order_notional=c.risk.max_order_notional,
            max_daily_loss_pct=c.risk.max_daily_loss_pct,
        ),
        mode=c.mode,
        desired_state=bot.desired_state,
        observed_state=bot.observed_state,
        config_version=bot.config_version,
        last_heartbeat_at=bot.last_heartbeat_at,
        last_error=bot.last_error,
        created_at=bot.created_at,
        updated_at=bot.updated_at,
    )


def _risk(risk: RiskIn) -> RiskLimits:
    return RiskLimits(risk.max_position_fraction, risk.max_order_notional, risk.max_daily_loss_pct)


def _container(request: Request) -> Container:
    container: Container = request.app.state.container
    return container


@router.post("", response_model=BotOut, status_code=status.HTTP_201_CREATED)
async def create_bot(body: BotCreate, request: Request) -> BotOut:
    """Create a paper-trading bot. It starts stopped; call ``/start`` to run it."""
    config = BotConfig(
        name=body.name,
        strategy_type=body.strategy_type,
        strategy_params=body.strategy_params,
        symbol=body.symbol,
        timeframe=body.timeframe,
        initial_capital=body.initial_capital,
        fee_rate=body.fee_rate,
        slippage_bps=body.slippage_bps,
        risk=_risk(body.risk),
        mode=ExecutionMode(body.mode),
    )
    return _out(await _container(request).bots.create(config))


@router.get("", response_model=list[BotOut])
async def list_bots(request: Request, limit: Limit = 100) -> list[BotOut]:
    return [_out(b) for b in await _container(request).bots.list_bots(limit)]


@router.get("/{bot_id}", response_model=BotOut)
async def get_bot(bot_id: UUID, request: Request) -> BotOut:
    return _out(await _container(request).bots.get(bot_id))


@router.patch("/{bot_id}", response_model=BotOut)
async def update_bot(bot_id: UUID, body: BotUpdate, request: Request) -> BotOut:
    """Change the configuration of a stopped bot (creates a new config version)."""
    changes: dict[str, Any] = body.model_dump(exclude_unset=True, exclude={"risk"})
    changes = {k: v for k, v in changes.items() if v is not None}
    if body.risk is not None:
        changes["risk"] = _risk(body.risk)
    return _out(await _container(request).bots.update(bot_id, changes))


@router.post("/{bot_id}/start", response_model=BotOut, status_code=status.HTTP_202_ACCEPTED)
async def start_bot(bot_id: UUID, request: Request) -> BotOut:
    """Ask the worker to run the bot (or resume it). Poll the bot for ``observed_state``."""
    return _out(await _container(request).bots.start(bot_id))


@router.post("/{bot_id}/pause", response_model=BotOut, status_code=status.HTTP_202_ACCEPTED)
async def pause_bot(bot_id: UUID, request: Request) -> BotOut:
    """Stop evaluating the strategy; the session and its state are kept."""
    return _out(await _container(request).bots.pause(bot_id))


@router.post("/{bot_id}/stop", response_model=BotOut, status_code=status.HTTP_202_ACCEPTED)
async def stop_bot(bot_id: UUID, request: Request) -> BotOut:
    """End the session. The virtual portfolio (including any open position) is kept."""
    return _out(await _container(request).bots.stop(bot_id))


@router.post("/{bot_id}/reset-portfolio", status_code=status.HTTP_204_NO_CONTENT)
async def reset_portfolio(bot_id: UUID, request: Request) -> Response:
    """Restart the virtual portfolio from the initial capital (stopped bots only)."""
    await _container(request).bots.reset_portfolio(bot_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{bot_id}/orders", response_model=list[OrderOut])
async def get_orders(bot_id: UUID, request: Request, limit: Limit = 100) -> list[OrderOut]:
    orders = await _container(request).bots.orders(bot_id, limit)
    return [
        OrderOut(
            id=o.id,
            client_order_id=o.client_order_id,
            symbol=o.symbol,
            side=o.side,
            quantity=o.quantity,
            status=o.status,
            filled_quantity=o.filled_quantity,
            avg_fill_price=o.avg_fill_price,
            reject_reason=o.reject_reason,
            bar_time=o.bar_time,
            created_at=o.created_at,
        )
        for o in orders
    ]


@router.get("/{bot_id}/signals", response_model=list[SignalOut])
async def get_signals(bot_id: UUID, request: Request, limit: Limit = 100) -> list[SignalOut]:
    """Strategy signals and what the risk layer decided (approved / rejected / discarded_stale)."""
    signals = await _container(request).bots.signals(bot_id, limit)
    return [
        SignalOut(
            bar_time=s.bar_time,
            side=s.side,
            kind=s.kind,
            reason=s.reason,
            decision=s.decision,
            decision_reason=s.decision_reason,
            created_at=s.created_at,
        )
        for s in signals
    ]


@router.get("/{bot_id}/portfolio", response_model=PortfolioOut)
async def get_portfolio(bot_id: UUID, request: Request) -> PortfolioOut:
    view = await _container(request).bots.portfolio(bot_id)
    return PortfolioOut(
        initial_capital=view.initial_capital,
        cash=view.cash,
        quantity=view.quantity,
        avg_entry_price=view.avg_entry_price,
        last_price=view.last_price,
        equity=view.equity,
        unrealized_pnl=view.unrealized_pnl,
        realized_pnl=view.realized_pnl,
        fees_paid=view.fees_paid,
    )


@router.get("/{bot_id}/performance", response_model=MetricsOut | None)
async def get_performance(bot_id: UUID, request: Request) -> MetricsOut | None:
    """Performance metrics net of fees (null until the bot has produced a snapshot)."""
    metrics = await _container(request).bots.performance(bot_id)
    return MetricsOut.model_validate(metrics.to_dict()) if metrics else None


@router.get("/{bot_id}/equity", response_model=list[EquityPointOut])
async def get_equity(bot_id: UUID, request: Request, limit: Limit = 500) -> list[EquityPointOut]:
    curve = await _container(request).bots.equity_curve(bot_id, limit)
    return [EquityPointOut(time=p.time, equity=p.equity) for p in curve]
