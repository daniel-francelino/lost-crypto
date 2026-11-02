"""Risk sizing rules for isolated linear perpetual entries."""

from collections.abc import Sequence
from decimal import Decimal

from modules.exchanges.domain.models import LeverageTier, PositionSide
from modules.execution.domain.fills import slipped_price
from modules.execution.domain.normalizer import OrderRejected
from modules.market_data.domain.models import Candle
from modules.portfolio.domain.perpetuals import LinearPerpetualPosition
from modules.risk_management.domain.models import (
    RiskLimits,
    candle_range_pct,
    close_jump_pct,
)
from modules.strategies.domain.types import Side, Signal, SignalKind


def size_linear_perpetual_entry(
    signal: Signal,
    *,
    equity: Decimal,
    available_collateral: Decimal,
    reference_price: Decimal,
    leverage: int,
    fee_rate: Decimal,
    slippage_bps: Decimal,
    limits: RiskLimits,
    candle: Candle,
    average_quote_volume: Decimal | None = None,
    leverage_tiers: Sequence[LeverageTier] = (),
    allow_short: bool = False,
    kill_switch_active: bool = False,
    previous_close: Decimal | None = None,
) -> Decimal:
    """Return quantity for a directional entry, or reject it before order creation.

    This is shared by paper, backtest and exchange execution. It never treats futures
    collateral as spot cash and does not use a candle close as a liquidation mark.
    """
    if signal.kind is not SignalKind.ENTRY:
        raise OrderRejected("perpetual sizing only accepts entry signals")
    if reference_price <= 0 or equity <= 0 or available_collateral <= 0:
        raise OrderRejected("no positive price, equity or available collateral")

    side = PositionSide.LONG if signal.side is Side.BUY else PositionSide.SHORT
    if side is PositionSide.SHORT and not allow_short:
        raise OrderRejected("short entries are disabled")
    if kill_switch_active:
        raise OrderRejected("kill switch is active")
    if (
        limits.max_candle_range_pct is not None
        and candle_range_pct(candle.high, candle.low) > limits.max_candle_range_pct
    ):
        raise OrderRejected("candle range exceeds the configured maximum")
    jump = close_jump_pct(candle.close, previous_close)
    if (
        limits.max_close_jump_pct is not None
        and jump is not None
        and jump > limits.max_close_jump_pct
    ):
        raise OrderRejected("close jump exceeds the configured maximum")
    if limits.require_stop_loss and signal.stop_loss is None:
        raise OrderRejected("a stop-loss is required but the signal has none")
    if signal.stop_loss is not None:
        valid_stop = (
            signal.stop_loss < reference_price
            if side is PositionSide.LONG
            else signal.stop_loss > reference_price
        )
        if signal.stop_loss <= 0 or not valid_stop:
            raise OrderRejected("stop-loss is on the wrong side of the entry")
    if signal.take_profit is not None:
        valid_target = (
            signal.take_profit > reference_price
            if side is PositionSide.LONG
            else 0 < signal.take_profit < reference_price
        )
        if not valid_target:
            raise OrderRejected("take-profit is on the wrong side of the entry")

    entry = slipped_price(signal.side, reference_price, slippage_bps)
    collateral_budget = min(available_collateral, equity * limits.max_position_fraction)
    max_notional = collateral_budget * leverage / (1 + fee_rate * leverage)
    if limits.max_order_notional is not None:
        max_notional = min(max_notional, limits.max_order_notional)
    if limits.max_order_pct_of_volume is not None and average_quote_volume is not None:
        max_notional = min(
            max_notional,
            average_quote_volume * limits.max_order_pct_of_volume / Decimal(100),
        )
    if max_notional <= 0:
        raise OrderRejected("no collateral remains for a new position")
    quantity = max_notional / entry

    if limits.max_risk_per_trade_pct is not None:
        if signal.stop_loss is None:
            raise OrderRejected("risk-per-trade sizing requires a stop-loss")
        distance = abs(entry - signal.stop_loss)
        round_trip_fees = (entry + signal.stop_loss) * fee_rate
        per_unit_risk = distance + round_trip_fees
        if per_unit_risk <= 0:
            raise OrderRejected("stop-loss risk distance must be positive")
        risk_budget = equity * limits.max_risk_per_trade_pct / Decimal(100)
        quantity = min(quantity, risk_budget / per_unit_risk)

    if limits.min_liquidation_distance_pct is not None:
        notional = quantity * entry
        tier = next(
            (item for item in leverage_tiers if item.supports(notional, leverage)), None
        )
        if tier is None:
            raise OrderRejected("no supported leverage tier covers the sized position")
        position = LinearPerpetualPosition(
            side,
            quantity,
            entry,
            leverage,
            notional / leverage,
        )
        liquidation_price = position.estimated_liquidation_price(
            tier.maintenance_margin_rate, tier.cumulative_maintenance_amount
        )
        distance_pct = (
            (entry - liquidation_price) / entry * Decimal(100)
            if side is PositionSide.LONG
            else (liquidation_price - entry) / entry * Decimal(100)
        )
        if distance_pct < limits.min_liquidation_distance_pct:
            raise OrderRejected(
                f"estimated liquidation buffer {distance_pct:.2f}% is below configured "
                f"{limits.min_liquidation_distance_pct}%"
            )
    return quantity
