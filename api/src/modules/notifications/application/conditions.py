"""What is wrong right now, as pure functions of the system's state.

Messages are kept stable while a condition lasts (no ages or counters that change every check),
so an open alert is only rewritten when something meaningful changes.
"""

from collections.abc import Sequence
from datetime import datetime, timedelta
from decimal import Decimal

from modules.bots.domain.models import Bot, BotState, ExecutionMode
from modules.execution.domain.orders import Order, OrderStatus, realized_slippage_bps
from modules.market_data.application.updater import UpdateReport
from modules.notifications.domain.models import AlertKind, AlertSeverity, Condition
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
