"""Protective exits (stop-loss / take-profit), shared by the backtester and the paper trader."""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from modules.exchanges.domain.models import PositionSide
from modules.market_data.domain.models import Candle


class ExitReason(StrEnum):
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"


@dataclass(frozen=True, slots=True)
class ProtectiveExit:
    reason: ExitReason
    trigger_price: Decimal  # reference price the exit executes at (before slippage)


def check_protective_exit(
    candle: Candle,
    stop_price: Decimal | None,
    take_profit_price: Decimal | None,
    side: PositionSide = PositionSide.LONG,
) -> ProtectiveExit | None:
    """Did a position's stop or target trigger inside this candle?

    Conservative assumptions: when both levels sit inside the candle's range the stop is
    assumed to have been hit first, and a gap through the stop fills at the open (worse than
    the stop). Take-profit fills at its level even on a favourable gap. ``LONG`` is the default
    to preserve the existing Spot call sites.
    """
    if side is PositionSide.LONG:
        if stop_price is not None and candle.low <= stop_price:
            price = candle.open if candle.open <= stop_price else stop_price
            return ProtectiveExit(ExitReason.STOP_LOSS, price)
        if take_profit_price is not None and candle.high >= take_profit_price:
            return ProtectiveExit(ExitReason.TAKE_PROFIT, take_profit_price)
    else:
        if stop_price is not None and candle.high >= stop_price:
            price = candle.open if candle.open >= stop_price else stop_price
            return ProtectiveExit(ExitReason.STOP_LOSS, price)
        if take_profit_price is not None and candle.low <= take_profit_price:
            return ProtectiveExit(ExitReason.TAKE_PROFIT, take_profit_price)
    return None
