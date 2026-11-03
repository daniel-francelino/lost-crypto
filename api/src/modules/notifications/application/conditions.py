"""What is wrong right now, as pure functions of the system's state.

Messages are kept stable while a condition lasts (no ages or counters that change every check),
so an open alert is only rewritten when something meaningful changes.
"""

from collections.abc import Sequence
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID

from modules.bots.domain.models import Bot, BotState, ExecutionMode
from modules.exchanges.domain.models import PositionSide, TradingProduct
from modules.execution.domain.orders import Order, OrderStatus, realized_slippage_bps
from modules.market_data.application.updater import UpdateReport
from modules.notifications.domain.models import AlertKind, AlertSeverity, Condition
from modules.portfolio.domain.perpetuals import PerpetualLedger
from modules.trading.application.status import SystemStatus

_MAX_MESSAGE = 300


def worker_down(status: SystemStatus) -> list[Condition]:
    if status.worker.alive:
        return []
    since = status.worker.last_heartbeat_at
    message = (
        "The worker has never reported a heartbeat."
        if since is None
        else f"No worker heartbeat since {since.isoformat()}."
    )
    return [
        Condition(
            AlertKind.WORKER_DOWN,
            "worker_down",
            AlertSeverity.CRITICAL,
            message,
            payload={"last_heartbeat_at": since.isoformat() if since else None},
        )
    ]


def kill_switch(status: SystemStatus) -> list[Condition]:
    if not status.kill_switch.active:
        return []
    reason = status.kill_switch.reason
    return [
        Condition(
            AlertKind.KILL_SWITCH_ACTIVE,
            "kill_switch",
            AlertSeverity.WARNING,
            f"The kill switch is active: {reason}" if reason else "The kill switch is active.",
        )
    ]


def bots(status: SystemStatus, active_bots: Sequence[Bot]) -> list[Condition]:
    """Bots that stopped advancing or ended in the error state. A live bot is critical."""
    by_id = {str(b.id): b for b in active_bots}
    out: list[Condition] = []
    for stale in status.stale_bots:
        bot = by_id.get(stale.bot_id)
        out.append(
            Condition(
                AlertKind.BOT_STALE,
                f"bot_stale:{stale.bot_id}",
                _severity(bot),
                f"Bot '{stale.name}' is running but its heartbeat is stale.",
                bot_id=bot.id if bot else None,
                payload={
                    "last_heartbeat_at": stale.last_heartbeat_at.isoformat()
                    if stale.last_heartbeat_at
                    else None
                },
            )
        )
    for bot in active_bots:
        if bot.observed_state is not BotState.ERROR:
            continue
        detail = (bot.last_error or "the bot stopped with an error")[:_MAX_MESSAGE]
        out.append(
            Condition(
                AlertKind.BOT_ERROR,
                f"bot_error:{bot.id}",
                _severity(bot),
                f"Bot '{bot.config.name}': {detail}",
                bot_id=bot.id,
            )
        )
    return out


def futures_unprotected_positions(status: SystemStatus) -> list[Condition]:
    """Alert when a live exchange-backed perpetual has no confirmed native stop order."""
    return [
        Condition(
            AlertKind.FUTURES_UNPROTECTED_POSITION,
            f"futures_unprotected_position:{position.bot_id}",
            AlertSeverity.WARNING,
            f"Futures '{position.name}' está sem stop ativo na Binance; uma queda do worker pode "
            "deixar a posição sem proteção.",
            bot_id=UUID(position.bot_id),
            payload={
                "symbol": position.symbol,
                "mode": position.mode,
                "quantity": str(position.quantity),
                "stop_price": str(position.stop_price) if position.stop_price is not None else None,
            },
        )
        for position in status.unprotected_positions
        if position.product == "linear_perpetual"
    ]


FUTURES_MARK_STALE_AFTER = timedelta(seconds=15)
DEFAULT_LIQUIDATION_BUFFER_PCT = Decimal("10")
FUNDING_COST_WARNING_PCT = Decimal("1")
FUNDING_COST_CRITICAL_PCT = Decimal("2")


def futures_position_risk(
    bot_ledgers: Sequence[tuple[Bot, PerpetualLedger]],
    now: datetime,
    mark_stale_after: timedelta = FUTURES_MARK_STALE_AFTER,
) -> list[Condition]:
    """Report stale Demo marks and narrowing isolated-margin distance to liquidation.

    The liquidation distance uses Binance's reported price when available, otherwise the local
    estimate. The source is included in the payload so the UI never presents an estimate as an
    exchange fact.
    """
    out: list[Condition] = []
    for bot, ledger in bot_ledgers:
        if (
            bot.config.product is not TradingProduct.LINEAR_PERPETUAL
            or bot.config.mode is not ExecutionMode.TESTNET
            or ledger.position is None
        ):
            continue
        position = ledger.position
        if (
            ledger.mark_price is None
            or ledger.marked_at is None
            or now - ledger.marked_at > mark_stale_after
            or now - ledger.marked_at < timedelta(seconds=-5)
        ):
            out.append(
                Condition(
                    AlertKind.FUTURES_MARK_STALE,
                    f"futures_mark_stale:{bot.id}",
                    AlertSeverity.WARNING,
                    f"Futures '{bot.config.name}' está sem uma marcação recente da Binance.",
                    bot_id=bot.id,
                    payload={
                        "symbol": bot.config.symbol,
                        "marked_at": ledger.marked_at.isoformat() if ledger.marked_at else None,
                        "max_age_seconds": int(mark_stale_after.total_seconds()),
                    },
                )
            )
            continue
        if ledger.mark_price is None:
            continue
        exchange_liquidation = ledger.exchange_liquidation_price
        liquidation = exchange_liquidation or ledger.liquidation_estimate(
            ledger.maintenance_margin_rate
        )
        if liquidation is None:
            continue
        distance = (
            (ledger.mark_price - liquidation) / ledger.mark_price
            if position.side is PositionSide.LONG
            else (liquidation - ledger.mark_price) / ledger.mark_price
        ) * 100
        configured_buffer = bot.config.risk.min_liquidation_distance_pct
        threshold = max(configured_buffer or Decimal(0), DEFAULT_LIQUIDATION_BUFFER_PCT)
        if distance > threshold:
            continue
        severity = (
            AlertSeverity.CRITICAL
            if distance <= threshold / 2
            else AlertSeverity.WARNING
        )
        source = "binance_exchange" if exchange_liquidation is not None else "local_estimate"
        out.append(
            Condition(
                AlertKind.FUTURES_MARGIN_BUFFER,
                f"futures_margin_buffer:{bot.id}",
                severity,
                f"Futures '{bot.config.name}' está a {distance:.2f}% do preço de liquidação.",
                bot_id=bot.id,
                payload={
                    "symbol": bot.config.symbol,
                    "side": position.side.value,
                    "distance_pct": str(distance),
                    "threshold_pct": str(threshold),
                    "liquidation_price": str(liquidation),
                    "mark_price": str(ledger.mark_price),
                    "liquidation_price_source": source,
                },
            )
        )
    return out


def futures_recovery_required(bots: Sequence[Bot]) -> list[Condition]:
    """Keep stream, margin-call and reconciliation pauses visible until an operator resumes."""
    out: list[Condition] = []
    for bot in bots:
        if (
            bot.config.product is not TradingProduct.LINEAR_PERPETUAL
            or bot.config.mode is not ExecutionMode.TESTNET
            or bot.desired_state is BotState.STOPPED
            or bot.last_error is None
        ):
            continue
        reason = bot.last_error.lower()
        if bot.observed_state is not BotState.ERROR and not (
            reason.startswith("risk.futures_")
            or "reconciliation" in reason
            or "futures demo" in reason
        ):
            continue
        cause = (
            "O stream privado da Binance foi interrompido"
            if "user_stream_disconnected" in reason
            else "A Binance enviou um aviso de margem"
            if "margin_call" in reason
            else "A configuração Futures da conta mudou"
            if "account_config_changed" in reason
            else "A posição Futures precisa de reconciliação"
        )
        out.append(
            Condition(
                AlertKind.FUTURES_RECOVERY_REQUIRED,
                f"futures_recovery_required:{bot.id}",
                AlertSeverity.WARNING,
                f"{cause} para '{bot.config.name}'. Revise a conta e reconcilie antes de retomar.",
                bot_id=bot.id,
                payload={"symbol": bot.config.symbol, "reason": bot.last_error},
            )
        )
    return out


def futures_funding_cost(
    bot_ledgers: Sequence[tuple[Bot, PerpetualLedger]],
) -> list[Condition]:
    """Warn when net funding paid becomes a material share of the bot's allocated capital."""
    out: list[Condition] = []
    for bot, ledger in bot_ledgers:
        if (
            bot.config.product is not TradingProduct.LINEAR_PERPETUAL
            or bot.config.mode is not ExecutionMode.TESTNET
            or bot.config.initial_capital <= 0
        ):
            continue
        net_paid = ledger.funding_paid - ledger.funding_received
        net_paid_pct = net_paid / bot.config.initial_capital * 100
        if net_paid_pct < FUNDING_COST_WARNING_PCT:
            continue
        severity = (
            AlertSeverity.CRITICAL
            if net_paid_pct >= FUNDING_COST_CRITICAL_PCT
            else AlertSeverity.WARNING
        )
        out.append(
            Condition(
                AlertKind.FUTURES_FUNDING_COST,
                f"futures_funding_cost:{bot.id}",
                severity,
                f"Funding líquido pago por '{bot.config.name}' atingiu "
                f"{net_paid_pct:.2f}% do capital alocado.",
                bot_id=bot.id,
                payload={
                    "symbol": bot.config.symbol,
                    "funding_paid": str(ledger.funding_paid),
                    "funding_received": str(ledger.funding_received),
                    "net_funding_paid": str(net_paid),
                    "net_funding_pct": str(net_paid_pct),
                    "warning_threshold_pct": str(FUNDING_COST_WARNING_PCT),
                    "critical_threshold_pct": str(FUNDING_COST_CRITICAL_PCT),
                },
            )
        )
    return out


def candles(report: UpdateReport) -> list[Condition]:
    out: list[Condition] = []
    for stale in report.stale:
        series = stale.series
        label = f"{series.exchange} {series.symbol} {series.timeframe.value}"
        out.append(
            Condition(
                AlertKind.CANDLES_STALE,
                f"candles_stale:{series.exchange}:{series.symbol}:{series.timeframe.value}",
                AlertSeverity.WARNING,
                f"Stored candles of {label} are behind; the last one opened at "
                f"{stale.last_open_time.isoformat()}.",
                payload={"last_open_time": stale.last_open_time.isoformat()},
            )
        )
    for pause in report.rate_limited:
        out.append(
            Condition(
                AlertKind.EXCHANGE_RATE_LIMITED,
                f"rate_limited:{pause.exchange}",
                AlertSeverity.WARNING,
                f"{pause.exchange} rate-limited candle updates; requests are paused until it "
                "clears.",
            )
        )
    return out


PROTECTIVE_ORDER_TYPE = "stop_loss"
_FLOOR_BPS = Decimal(10)  # a bot configured with no slippage still tolerates this much


def protective_slippage(
    bot_orders: Sequence[tuple[Bot, Sequence[Order]]],
    now: datetime,
    window: timedelta,
    multiple: Decimal,
) -> list[Condition]:
    """A protective exit that filled far worse than the bot's configured slippage (book 2 ch. 8,
    O4: stops can fill at absurd prices when liquidity vanishes). Only filled stop-loss orders of
    the window count; the message carries no numbers, so it stays stable while it lasts."""
    out: list[Condition] = []
    for bot, orders in bot_orders:
        limit = max(bot.config.slippage_bps, _FLOOR_BPS) * multiple
        worst = [
            slip
            for order in orders
            if order.order_type == PROTECTIVE_ORDER_TYPE
            and order.status is OrderStatus.FILLED
            and order.first_fill_at is not None
            and now - order.first_fill_at <= window
            and (slip := realized_slippage_bps(order)) is not None
            and slip > limit
        ]
        if worst:
            out.append(
                Condition(
                    AlertKind.PROTECTIVE_EXIT_SLIPPAGE,
                    f"protective_exit_slippage:{bot.id}",
                    _severity(bot),
                    f"Bot '{bot.config.name}': uma saída protetora preencheu com slippage muito "
                    "acima do configurado.",
                    bot_id=bot.id,
                    payload={"multiple": str(multiple)},
                )
            )
    return out


def _severity(bot: Bot | None) -> AlertSeverity:
    live = bot is not None and bot.config.mode is ExecutionMode.LIVE
    return AlertSeverity.CRITICAL if live else AlertSeverity.WARNING
