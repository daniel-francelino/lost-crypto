from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status
from pydantic import BaseModel, Field

from container import Container
from core.pagination import Offset, set_total
from core.security.auth import Principal, require_auth
from modules.analytics.presentation.schemas import MetricsOut
from modules.audit.schemas import NoteIn, NoteOut
from modules.bots.domain.models import Bot, BotConfig, BotState, ExecutionMode
from modules.exchanges.domain.models import MarginMode, PositionSide, TradingProduct
from modules.execution.domain.orders import OrderStatus, latency_ms, realized_slippage_bps
from modules.market_data.domain.models import Timeframe
from modules.risk_management.domain.models import RiskLimits
from modules.risk_management.presentation.schemas import RiskLimitsIn
from modules.strategies.domain.types import Side, SignalKind
from modules.trading.application.parity_store import ParityRun
from modules.trading.domain.comparison import CHAN_MIN_RATIO, MIN_PERIODS
from modules.trading.domain.diagnosis import VOLUME_MARKER, checklist, execution_quality

router = APIRouter(prefix="/bots", tags=["bots"])

Symbol = Annotated[
    str,
    Field(pattern=r"^[A-Z0-9]{2,15}/USDT(?::USDT)?$", examples=["BTC/USDT", "BTC/USDT:USDT"]),
]
Limit = Annotated[int, Query(ge=1, le=500)]


class StartIn(BaseModel):
    confirmation_token: str | None = Field(
        default=None,
        description="Live bots only: the single-use token from POST /bots/{id}/live-approvals",
    )


class ReasonIn(BaseModel):
    reason: str | None = Field(default=None, max_length=200)


class CheckOut(BaseModel):
    name: str
    ok: bool
    detail: str


class ReadinessOut(BaseModel):
    ready: bool
    checks: list[CheckOut]


class ApprovalIn(BaseModel):
    confirm_name: str = Field(description="Type the bot's exact name to confirm you mean it")


class ApprovalOut(BaseModel):
    confirmation_token: str = Field(description="Shown once. Valid for one start of this version")
    expires_at: datetime


class PromoteIn(BaseModel):
    connection_id: UUID = Field(description="An ACTIVE live connection of the bot's exchange")


RiskIn = RiskLimitsIn  # shared with backtests


class BotCreate(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    exchange: str = "binance"
    strategy_type: str = Field(examples=["trend_quality_breakout"])
    strategy_params: dict[str, Any] = Field(default_factory=dict)
    symbol: Symbol = "BTC/USDT"
    product: TradingProduct = TradingProduct.SPOT
    leverage: int = Field(default=1, ge=1, le=10)
    margin_mode: MarginMode | None = None
    allow_short: bool = False
    timeframe: Timeframe = Timeframe.H1
    initial_capital: Decimal = Field(default=Decimal(1000), gt=0)
    fee_rate: Decimal | None = Field(
        default=None, ge=0, lt=1, description="Defaults to the exchange's taker fee"
    )
    slippage_bps: Decimal = Field(default=Decimal(5), ge=0, lt=10000)
    risk: RiskIn = Field(default_factory=RiskIn)
    mode: Literal["paper", "testnet"] = "paper"  # live is not available yet
    connection_id: UUID | None = Field(
        default=None,
        description="Required for testnet bots and Futures paper (active Binance Demo connection)",
    )


class BotUpdate(BaseModel):
    """Every field optional. Only allowed while the bot is stopped."""

    name: str | None = Field(default=None, min_length=1, max_length=60)
    exchange: str | None = None
    strategy_type: str | None = None
    strategy_params: dict[str, Any] | None = None
    symbol: Symbol | None = None
    product: TradingProduct | None = None
    leverage: int | None = Field(default=None, ge=1, le=10)
    margin_mode: MarginMode | None = None
    allow_short: bool | None = None
    timeframe: Timeframe | None = None
    initial_capital: Decimal | None = Field(default=None, gt=0)
    fee_rate: Decimal | None = Field(default=None, ge=0, lt=1)
    slippage_bps: Decimal | None = Field(default=None, ge=0, lt=10000)
    risk: RiskIn | None = None
    mode: Literal["paper", "testnet"] | None = None  # live has its own endpoint
    connection_id: UUID | None = None
    change_reason: str | None = Field(default=None, max_length=200)


class BotOut(BaseModel):
    id: UUID
    name: str
    exchange: str
    strategy_type: str
    strategy_params: dict[str, Any]
    symbol: str
    product: TradingProduct
    leverage: int
    margin_mode: MarginMode | None
    allow_short: bool
    timeframe: Timeframe
    initial_capital: Decimal
    fee_rate: Decimal
    slippage_bps: Decimal
    risk: RiskIn
    mode: ExecutionMode
    connection_id: UUID | None
    desired_state: BotState
    observed_state: BotState
    config_version: int
    live_approved: bool
    live_approved_at: datetime | None
    last_heartbeat_at: datetime | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime


class OrderOut(BaseModel):
    id: UUID
    client_order_id: str
    order_type: str
    exchange_order_id: str | None
    symbol: str
    side: Side
    product: TradingProduct
    position_side: PositionSide | None
    leverage: int
    reduce_only: bool
    quantity: Decimal
    status: OrderStatus
    filled_quantity: Decimal
    avg_fill_price: Decimal | None
    reject_reason: str | None
    bar_time: datetime
    created_at: datetime
    reference_price: Decimal | None = Field(
        default=None, description="Price of the decision: signal candle close or stop trigger."
    )
    submitted_at: datetime | None = None
    first_fill_at: datetime | None = None
    slippage_bps: Decimal | None = Field(
        default=None, description="Adverse move from the reference to the fill (bps)."
    )
    latency_ms: int | None = Field(default=None, description="Decision to first fill.")


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
    stop_price: Decimal | None
    take_profit_price: Decimal | None
    reserved_cash: Decimal
    native_stop_active: bool
    product: TradingProduct = TradingProduct.SPOT
    position_side: PositionSide | None = None
    leverage: int = 1
    isolated_margin: Decimal = Decimal(0)
    reserved_margin: Decimal = Decimal(0)
    liquidation_price: Decimal | None = None
    funding_paid: Decimal = Decimal(0)
    funding_received: Decimal = Decimal(0)


class BotOverviewOut(BaseModel):
    id: UUID
    name: str
    mode: ExecutionMode
    exchange: str
    symbol: str
    timeframe: Timeframe
    strategy_type: str
    strategy_params: dict[str, Any]
    desired_state: BotState
    observed_state: BotState
    equity: Decimal
    return_pct: Decimal
    realized_pnl: Decimal
    fees_paid: Decimal
    in_position: bool
    last_price: Decimal | None
    last_heartbeat_at: datetime | None
    interventions_30d: int


class InterventionItemOut(BaseModel):
    at: datetime
    type: str
    actor: str
    reason: str | None
    drawdown_pct: Decimal | None


class InterventionsOut(BaseModel):
    days: int
    total: int
    after_drawdown: int
    drawdown_threshold_pct: Decimal
    by_type: dict[str, int]
    items: list[InterventionItemOut]
    system: dict[str, int]


class EquityPointOut(BaseModel):
    time: datetime
    equity: Decimal


def _out(bot: Bot) -> BotOut:
    c = bot.config
    return BotOut(
        id=bot.id,
        name=c.name,
        exchange=c.exchange,
        strategy_type=c.strategy_type,
        strategy_params=dict(c.strategy_params),
        symbol=c.symbol,
        product=c.product,
        leverage=c.leverage,
        margin_mode=c.margin_mode,
        allow_short=c.allow_short,
        timeframe=c.timeframe,
        initial_capital=c.initial_capital,
        fee_rate=c.fee_rate,
        slippage_bps=c.slippage_bps,
        risk=RiskIn.from_domain(c.risk),
        mode=c.mode,
        connection_id=c.connection_id,
        desired_state=bot.desired_state,
        observed_state=bot.observed_state,
        config_version=bot.config_version,
        live_approved=bot.has_live_approval,
        live_approved_at=bot.live_approved_at,
        last_heartbeat_at=bot.last_heartbeat_at,
        last_error=bot.last_error,
        created_at=bot.created_at,
        updated_at=bot.updated_at,
    )


def _risk(risk: RiskIn) -> RiskLimits:
    return risk.to_domain()


def _container(request: Request) -> Container:
    container: Container = request.app.state.container
    return container


@router.post("", response_model=BotOut, status_code=status.HTTP_201_CREATED)
async def create_bot(body: BotCreate, request: Request) -> BotOut:
    """Create a paper-trading bot. It starts stopped; call ``/start`` to run it."""
    bots = _container(request).bots
    config = BotConfig(
        name=body.name,
        exchange=body.exchange,
        strategy_type=body.strategy_type,
        strategy_params=body.strategy_params,
        symbol=body.symbol,
        product=body.product,
        leverage=body.leverage,
        margin_mode=body.margin_mode,
        allow_short=body.allow_short,
        timeframe=body.timeframe,
        initial_capital=body.initial_capital,
        fee_rate=(
            body.fee_rate if body.fee_rate is not None else bots.default_fee_rate(body.exchange)
        ),
        slippage_bps=body.slippage_bps,
        risk=_risk(body.risk),
        mode=ExecutionMode(body.mode),
        connection_id=body.connection_id,
    )
    return _out(await bots.create(config))


@router.get("", response_model=list[BotOut])
async def list_bots(request: Request, limit: Limit = 100) -> list[BotOut]:
    return [_out(b) for b in await _container(request).bots.list_bots(limit)]


class PortfolioSummaryOut(BaseModel):
    mode: ExecutionMode
    quote_currency: str
    bots: int
    running: int
    open_positions: int
    initial_capital: Decimal
    equity: Decimal
    realized_pnl: Decimal
    fees_paid: Decimal
    return_pct: Decimal


@router.get("/summary", response_model=list[PortfolioSummaryOut])
async def get_summary(request: Request) -> list[PortfolioSummaryOut]:
    """Equity, PnL and fees added up per execution mode and quote currency (never mixed)."""
    return [
        PortfolioSummaryOut(
            mode=g.mode,
            quote_currency=g.quote_currency,
            bots=g.bots,
            running=g.running,
            open_positions=g.open_positions,
            initial_capital=g.initial_capital,
            equity=g.equity,
            realized_pnl=g.realized_pnl,
            fees_paid=g.fees_paid,
            return_pct=g.return_pct,
        )
        for g in await _container(request).bots.summary()
    ]


@router.get("/overview", response_model=list[BotOverviewOut])
async def get_overview(request: Request) -> list[BotOverviewOut]:
    """Every bot with its current equity and return, for side-by-side comparison."""
    rows = await _container(request).bots.overview()
    return [
        BotOverviewOut(
            id=r.bot.id,
            name=r.bot.config.name,
            mode=r.bot.config.mode,
            exchange=r.bot.config.exchange,
            symbol=r.bot.config.symbol,
            timeframe=r.bot.config.timeframe,
            strategy_type=r.bot.config.strategy_type,
            strategy_params=dict(r.bot.config.strategy_params),
            desired_state=r.bot.desired_state,
            observed_state=r.bot.observed_state,
            equity=r.equity,
            return_pct=r.return_pct,
            realized_pnl=r.realized_pnl,
            fees_paid=r.fees_paid,
            in_position=r.in_position,
            last_price=r.last_price,
            last_heartbeat_at=r.bot.last_heartbeat_at,
            interventions_30d=r.interventions_30d,
        )
        for r in rows
    ]


@router.get("/{bot_id}", response_model=BotOut)
async def get_bot(bot_id: UUID, request: Request) -> BotOut:
    return _out(await _container(request).bots.get(bot_id))


@router.patch("/{bot_id}", response_model=BotOut)
async def update_bot(
    bot_id: UUID, body: BotUpdate, request: Request, principal: Principal = Depends(require_auth)
) -> BotOut:
    """Change the configuration of a stopped bot (creates a new config version)."""
    changes: dict[str, Any] = body.model_dump(exclude_unset=True, exclude={"risk", "change_reason"})
    changes = {k: v for k, v in changes.items() if v is not None}
    if body.risk is not None:
        changes["risk"] = _risk(body.risk)
    if body.mode is not None:
        changes["mode"] = ExecutionMode(body.mode)
        if body.mode == "paper":
            changes["connection_id"] = None  # a paper bot uses no exchange account
    return _out(
        await _container(request).bots.update(
            bot_id, changes, actor=principal.username, reason=body.change_reason
        )
    )


@router.post("/{bot_id}/start", response_model=BotOut, status_code=status.HTTP_202_ACCEPTED)
async def start_bot(
    bot_id: UUID,
    request: Request,
    body: StartIn | None = None,
    principal: Principal = Depends(require_auth),
) -> BotOut:
    """Ask the worker to run the bot (or resume it). Poll the bot for ``observed_state``.

    A **live** bot needs `confirmation_token` every time it starts (see live-approvals).
    """
    token = body.confirmation_token if body else None
    return _out(await _container(request).bots.start(bot_id, token, actor=principal.username))


@router.get("/{bot_id}/live-readiness", response_model=ReadinessOut)
async def live_readiness(bot_id: UUID, request: Request) -> ReadinessOut:
    """The checklist a bot must pass before it may trade real money (all items must be ok)."""
    readiness = await _container(request).bots.live_readiness(bot_id)
    return ReadinessOut(
        ready=readiness.ready,
        checks=[CheckOut(name=c.name, ok=c.ok, detail=c.detail) for c in readiness.checks],
    )


@router.post("/{bot_id}/promote-to-live", response_model=BotOut)
async def promote_to_live(bot_id: UUID, body: PromoteIn, request: Request) -> BotOut:
    """Point a stopped bot at a live connection. This does NOT start trading: it still needs
    the readiness checklist and a one-time approval."""
    return _out(await _container(request).bots.promote_to_live(bot_id, body.connection_id))


@router.post(
    "/{bot_id}/live-approvals",
    response_model=ApprovalOut,
    status_code=status.HTTP_201_CREATED,
)
async def request_live_approval(
    bot_id: UUID,
    body: ApprovalIn,
    request: Request,
    principal: Principal = Depends(require_auth),
) -> ApprovalOut:
    """Step 1 of starting a live bot: pass the checklist and type its name. Returns a token that
    is single-use, short-lived and valid only for the bot's current configuration."""
    issued = await _container(request).bots.request_live_approval(
        bot_id, body.confirm_name, principal.username
    )
    return ApprovalOut(confirmation_token=issued.token, expires_at=issued.expires_at)


@router.post("/{bot_id}/pause", response_model=BotOut, status_code=status.HTTP_202_ACCEPTED)
async def pause_bot(
    bot_id: UUID,
    request: Request,
    body: ReasonIn | None = None,
    principal: Principal = Depends(require_auth),
) -> BotOut:
    """Stop evaluating the strategy; the session and its state are kept."""
    return _out(
        await _container(request).bots.pause(
            bot_id, reason=body.reason if body else None, actor=principal.username
        )
    )


@router.post("/{bot_id}/stop", response_model=BotOut, status_code=status.HTTP_202_ACCEPTED)
async def stop_bot(
    bot_id: UUID,
    request: Request,
    body: ReasonIn | None = None,
    principal: Principal = Depends(require_auth),
) -> BotOut:
    """End the session. The virtual portfolio (including any open position) is kept."""
    return _out(
        await _container(request).bots.stop(
            bot_id, reason=body.reason if body else None, actor=principal.username
        )
    )


@router.post(
    "/{bot_id}/close-position",
    response_model=OrderOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def close_futures_position(
    bot_id: UUID,
    request: Request,
    body: ReasonIn | None = None,
    principal: Principal = Depends(require_auth),
) -> OrderOut:
    """Pause a Binance Demo Futures bot and submit a reduce-only market close."""
    order = await _container(request).perpetual_close.close(
        bot_id,
        actor=principal.username,
        reason=body.reason if body else None,
    )
    return OrderOut(
        id=order.id,
        client_order_id=order.client_order_id,
        order_type=order.order_type,
        exchange_order_id=order.exchange_order_id,
        symbol=order.symbol,
        side=order.side,
        product=order.product,
        position_side=order.position_side,
        leverage=order.leverage,
        reduce_only=order.reduce_only,
        quantity=order.quantity,
        status=order.status,
        filled_quantity=order.filled_quantity,
        avg_fill_price=order.avg_fill_price,
        reject_reason=order.reject_reason,
        bar_time=order.bar_time,
        created_at=order.created_at,
        reference_price=order.reference_price,
        submitted_at=order.submitted_at,
        first_fill_at=order.first_fill_at,
        slippage_bps=(
            None if (bps := realized_slippage_bps(order)) is None else bps.quantize(Decimal("0.01"))
        ),
        latency_ms=latency_ms(order),
    )


@router.delete("/{bot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bot(
    bot_id: UUID,
    request: Request,
    body: ReasonIn | None = None,
    principal: Principal = Depends(require_auth),
) -> Response:
    """Delete a stopped bot with its orders, signals, portfolio and history. The audit trail
    keeps a `bot.deleted` event. Live bots and bots with an open position are refused (409)."""
    await _container(request).bots.delete(
        bot_id, reason=body.reason if body else None, actor=principal.username
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{bot_id}/reset-portfolio", status_code=status.HTTP_204_NO_CONTENT)
async def reset_portfolio(
    bot_id: UUID,
    request: Request,
    body: ReasonIn | None = None,
    principal: Principal = Depends(require_auth),
) -> Response:
    """Restart the virtual portfolio from the initial capital (stopped bots only)."""
    await _container(request).bots.reset_portfolio(
        bot_id, reason=body.reason if body else None, actor=principal.username
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{bot_id}/interventions", response_model=InterventionsOut)
async def get_interventions(
    bot_id: UUID, request: Request, days: int = Query(default=30, ge=1, le=365)
) -> InterventionsOut:
    return InterventionsOut.model_validate(
        await _container(request).bots.interventions(bot_id, days)
    )


@router.get("/{bot_id}/orders", response_model=list[OrderOut])
async def get_orders(
    bot_id: UUID, request: Request, response: Response, limit: Limit = 100, offset: Offset = 0
) -> list[OrderOut]:
    orders, total = await _container(request).bots.orders(bot_id, limit, offset)
    set_total(response, total)
    return [
        OrderOut(
            id=o.id,
            client_order_id=o.client_order_id,
            order_type=o.order_type,
            exchange_order_id=o.exchange_order_id,
            symbol=o.symbol,
            side=o.side,
            product=o.product,
            position_side=o.position_side,
            leverage=o.leverage,
            reduce_only=o.reduce_only,
            quantity=o.quantity,
            status=o.status,
            filled_quantity=o.filled_quantity,
            avg_fill_price=o.avg_fill_price,
            reject_reason=o.reject_reason,
            bar_time=o.bar_time,
            created_at=o.created_at,
            reference_price=o.reference_price,
            submitted_at=o.submitted_at,
            first_fill_at=o.first_fill_at,
            slippage_bps=None
            if (bps := realized_slippage_bps(o)) is None
            else bps.quantize(Decimal("0.01")),
            latency_ms=latency_ms(o),
        )
        for o in orders
    ]


@router.get("/{bot_id}/signals", response_model=list[SignalOut])
async def get_signals(
    bot_id: UUID, request: Request, response: Response, limit: Limit = 100, offset: Offset = 0
) -> list[SignalOut]:
    """Strategy signals and what the risk layer decided (approved / rejected / discarded_stale)."""
    signals, total = await _container(request).bots.signals(bot_id, limit, offset)
    set_total(response, total)
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
        stop_price=view.stop_price,
        take_profit_price=view.take_profit_price,
        reserved_cash=view.reserved_cash,
        native_stop_active=view.native_stop_active,
        product=view.product,
        position_side=view.position_side,
        leverage=view.leverage,
        isolated_margin=view.isolated_margin,
        reserved_margin=view.reserved_margin,
        liquidation_price=view.liquidation_price,
        funding_paid=view.funding_paid,
        funding_received=view.funding_received,
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


# --- execution systems (book 1 ch. 5) -------------------------------------------------------

ALL_RECORDS = 20_000


class ExecutionQualityOut(BaseModel):
    configured_slippage_bps: Decimal
    by_type: dict[str, Any] = Field(
        description="Per order type: orders, slippage_bps {mean, median, worst}, latency_ms "
        "{mean, max}."
    )
    above_configured: bool = Field(
        description="Realized market-order slippage above the assumption (+1 bps tolerance)."
    )


@router.get("/{bot_id}/execution-quality", response_model=ExecutionQualityOut)
async def get_execution_quality(bot_id: UUID, request: Request) -> ExecutionQualityOut:
    """Realized slippage and latency of the bot's filled orders against its assumption."""
    container = _container(request)
    bot = await container.bots.get(bot_id)
    orders, _ = await container.bots.orders(bot_id, ALL_RECORDS, 0)
    return ExecutionQualityOut.model_validate(execution_quality(orders, bot.config.slippage_bps))


class ParityOut(BaseModel):
    id: UUID
    status: str = Field(description="queued | running | completed | failed")
    created_at: datetime
    finished_at: datetime | None
    unexplained: int | None
    summary: dict[str, Any] | None = Field(
        description="counts by class, verdict, differences, returns, replay_equity."
    )
    error: str | None


def _parity_out(run: ParityRun) -> ParityOut:
    return ParityOut(
        id=run.id,
        status=run.status,
        created_at=run.created_at,
        finished_at=run.finished_at,
        unexplained=run.unexplained,
        summary=run.summary,
        error=run.error,
    )


@router.post("/{bot_id}/parity", response_model=ParityOut, status_code=status.HTTP_202_ACCEPTED)
async def request_parity(bot_id: UUID, request: Request) -> ParityOut:
    """Queue a replay of the bot's latest session through the backtester (the worker runs it)
    and a comparison of signals and trades. Read-only: the bot is not affected."""
    return _parity_out(await _container(request).parity.request(bot_id))


@router.get("/{bot_id}/parity", response_model=ParityOut | None)
async def get_parity(bot_id: UUID, request: Request) -> ParityOut | None:
    run = await _container(request).parity.latest(bot_id)
    return None if run is None else _parity_out(run)


@router.post("/{bot_id}/notes", response_model=NoteOut, status_code=status.HTTP_201_CREATED)
async def add_bot_note(
    bot_id: UUID,
    body: NoteIn,
    request: Request,
    principal: Principal = Depends(require_auth),
) -> NoteOut:
    """Record why this bot was paused, changed or retired. Stored in the audit trail
    (`note.added`); read it with `GET /audit-events?event_type=note.added&entity_id={bot_id}`."""
    container = _container(request)
    await container.bots.get(bot_id)
    await container.audit.add_note("bot", str(bot_id), bot_id, principal.username, body.text)
    return NoteOut(actor=principal.username, text=body.text)


class RealizedSharpeOut(BaseModel):
    sharpe: Decimal | None = Field(description="Annualised (365 days); null on a short sample.")
    return_periods: int | None = Field(description="The size of the live sample.")
    days: Decimal | None


class BacktestSharpeOut(BaseModel):
    sharpe: Decimal | None


class RealizedVsBacktestOut(BaseModel):
    run_id: UUID | None = Field(description="The backtest compared with; null if none matches.")
    run_created_at: datetime | None
    realized: RealizedSharpeOut | None
    backtest: BacktestSharpeOut | None
    ratio: Decimal | None = Field(description="Realized Sharpe / backtest Sharpe.")
    min_periods: int = Field(description="Live returns needed before a ratio is given.")
    chan_min_ratio: Decimal = Field(
        description="Chan's rule of thumb (his experience, not a standard): a ratio of at "
        "least this is usually acceptable."
    )
    reason: str | None = Field(description="Why there is no ratio, when there is none.")


@router.get("/{bot_id}/backtest-comparison", response_model=RealizedVsBacktestOut)
async def get_backtest_comparison(
    bot_id: UUID, request: Request, run_id: UUID | None = None
) -> RealizedVsBacktestOut:
    """Compare the bot's realized Sharpe with the backtest of its configuration (the newest
    completed one with the same strategy parameters, or ``run_id``). Read-only."""
    result = await _container(request).comparison.compare(bot_id, run_id)
    comparison = result.comparison
    return RealizedVsBacktestOut(
        run_id=result.run_id,
        run_created_at=result.run_created_at,
        realized=None
        if comparison is None
        else RealizedSharpeOut(
            sharpe=comparison.realized,
            return_periods=comparison.realized_periods,
            days=result.realized_days,
        ),
        backtest=None if comparison is None else BacktestSharpeOut(sharpe=comparison.backtest),
        ratio=None if comparison is None else comparison.ratio,
        min_periods=MIN_PERIODS,
        chan_min_ratio=CHAN_MIN_RATIO,
        reason=result.reason if comparison is None else comparison.reason,
    )


class StepOut(BaseModel):
    key: str = Field(description="bugs | trades | costs | liquidity | snooping | regime")
    state: str = Field(description="ok | attention | no_data")
    detail: str
    values: dict[str, str | int | None] = Field(
        default_factory=dict, description="The numbers behind the detail."
    )


@router.get("/{bot_id}/divergence", response_model=list[StepOut])
async def get_divergence(bot_id: UUID, request: Request) -> list[StepOut]:
    """Chan's checklist for "why does it differ from the backtest?", in his order. Never
    concludes bad luck: it cannot be proven."""
    container = _container(request)
    bot = await container.bots.get(bot_id)
    orders, _ = await container.bots.orders(bot_id, ALL_RECORDS, 0)
    signals, _ = await container.bots.signals(bot_id, ALL_RECORDS, 0)
    parity = await container.parity.latest(bot_id)
    summary = parity.summary if parity is not None and parity.status == "completed" else None
    volume_refusals = sum(1 for s in signals if VOLUME_MARKER in (s.decision_reason or ""))
    steps = checklist(
        summary,
        execution_quality(orders, bot.config.slippage_bps),
        volume_refusals,
        await _regime(container, bot, summary),
    )
    return [
        StepOut(key=s.key, state=s.state.value, detail=s.detail, values=s.values) for s in steps
    ]


async def _regime(
    container: Container, bot: Bot, summary: dict[str, Any] | None
) -> tuple[Decimal, Decimal] | None:
    """Bot return vs the worst period of the latest comparable backtest (same strategy,
    parameters, symbol and timeframe)."""
    if summary is None or summary.get("bot_return_pct") is None:
        return None
    runs, _ = await container.backtests.list_runs(200, 0)
    cfg = bot.config
    for run in runs:
        c = run.config
        if (
            run.periods
            and c.strategy_type == cfg.strategy_type
            and c.symbol == cfg.symbol
            and c.product is cfg.product
            and c.leverage == cfg.leverage
            and c.margin_mode == cfg.margin_mode
            and c.allow_short == cfg.allow_short
            and c.timeframe is cfg.timeframe
            and dict(c.strategy_params) == dict(cfg.strategy_params)
        ):
            worst = min(Decimal(p["metrics"]["total_return_pct"]) for p in run.periods["periods"])
            return Decimal(summary["bot_return_pct"]), worst
    return None
