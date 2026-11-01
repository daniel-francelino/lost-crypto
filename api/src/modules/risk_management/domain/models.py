"""Risk rules as pure functions: every signal goes through ``assess_signal`` before an order."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from core.errors import DomainError
from modules.execution.domain.fills import affordable_buy_quantity, slipped_price
from modules.execution.domain.normalizer import OrderRejected, normalize_quantity
from modules.market_data.domain.models import MarketInfo
from modules.portfolio.domain.models import PortfolioState
from modules.strategies.domain.types import Side, Signal

_PCT = Decimal(100)


class InvalidRiskLimits(DomainError):
    pass


class DrawdownAction(StrEnum):
    """What a bot does when ``max_drawdown_pct`` is breached (book 2 ch. 8, O2).

    ``pause`` waits for the operator and can simply be resumed; ``stop`` ends the session, because
    a budget that is spent ends the strategy. Either way the position is kept and exits stay
    allowed."""

    PAUSE = "pause"
    STOP = "stop"


@dataclass(frozen=True, slots=True)
class RiskLimits:
    """Per-bot limits. ``None`` disables a limit."""

    max_position_fraction: Decimal = Decimal(1)  # share of equity a position may use (0, 1]
    max_order_notional: Decimal | None = None  # hard cap per order, in quote currency
    max_daily_loss_pct: Decimal | None = Decimal(10)  # pause beyond this loss in a UTC day
    max_drawdown_pct: Decimal | None = None  # pause beyond this drop from the equity peak
    max_consecutive_losses: int | None = None  # pause after N losing round trips in a row
    max_risk_per_trade_pct: Decimal | None = None  # equity % lost if the stop is hit (sizing)
    require_stop_loss: bool = False  # refuse entries that come without a stop-loss
    max_candle_range_pct: Decimal | None = Decimal(25)  # refuse entries on suspect candles
    # An order may use at most this % of the average quote volume of the last candles
    # (book 1 ch. 5, O5: Chan's rule of thumb is ~1% of daily volume for stocks). None = off.
    max_order_pct_of_volume: Decimal | None = None
    # Refuse entries when the candle's close moved more than this % from the previous close
    # (book 2 ch. 3, O5: a bad tick often shows as a jump, not as a wide candle). None = off.
    max_close_jump_pct: Decimal | None = None
    drawdown_action: DrawdownAction = DrawdownAction.PAUSE

    def __post_init__(self) -> None:
        if not (0 < self.max_position_fraction <= 1):
            raise InvalidRiskLimits("max_position_fraction must be in (0, 1]")
        if self.max_order_notional is not None and self.max_order_notional <= 0:
            raise InvalidRiskLimits("max_order_notional must be positive")
        for name in ("max_daily_loss_pct", "max_drawdown_pct", "max_risk_per_trade_pct"):
            value = getattr(self, name)
            if value is not None and not (0 < value <= 100):
                raise InvalidRiskLimits(f"{name} must be in (0, 100]")
        if self.max_consecutive_losses is not None and self.max_consecutive_losses < 1:
            raise InvalidRiskLimits("max_consecutive_losses must be at least 1")
        if self.max_candle_range_pct is not None and self.max_candle_range_pct <= 0:
            raise InvalidRiskLimits("max_candle_range_pct must be positive")
        if self.max_close_jump_pct is not None and self.max_close_jump_pct <= 0:
            raise InvalidRiskLimits("max_close_jump_pct must be positive")
        volume = self.max_order_pct_of_volume
        if volume is not None and not (0 < volume <= 100):
            raise InvalidRiskLimits("max_order_pct_of_volume must be in (0, 100]")


@dataclass(frozen=True, slots=True)
class GlobalRiskLimits:
    """Limits across all bots. Configured by the operator (environment), not via the API."""

    max_open_positions: int | None = None
    max_total_exposure: Decimal | None = None  # sum of open position cost, quote currency


@dataclass(frozen=True, slots=True)
class LiveLimits:
    """Hard caps for real money, set by the operator in the environment (never via the API, never
    per bot). They bound the blast radius even if a bot's own configuration is wrong."""

    max_order_notional: Decimal | None = None
    max_total_exposure: Decimal | None = None
    max_daily_loss: Decimal | None = None  # absolute amount, per bot per UTC day

    @property
    def complete(self) -> bool:
        return None not in (self.max_order_notional, self.max_total_exposure, self.max_daily_loss)


@dataclass(frozen=True, slots=True)
class GlobalExposure:
    open_positions: int = 0
    notional: Decimal = Decimal(0)


@dataclass(frozen=True, slots=True)
class RiskDecision:
    approved: bool
    quantity: Decimal | None = None
    reason: str | None = None

    @classmethod
    def reject(cls, reason: str) -> "RiskDecision":
        return cls(approved=False, reason=reason)


@dataclass(frozen=True, slots=True)
class BackupRecord:
    kind: str  # "backup" | "restore_check"
    at: datetime
    ok: bool
    file: str | None = None
    size_bytes: int | None = None
    checksum: str | None = None
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class KillSwitchState:
    active: bool = False
    reason: str | None = None
    changed_at: datetime | None = None


def candle_range_pct(high: Decimal, low: Decimal) -> Decimal:
    return (high - low) / low * _PCT if low > 0 else Decimal(0)


def close_jump_pct(close: Decimal, previous_close: Decimal | None) -> Decimal | None:
    """Absolute % move of the close from the previous close; None without a previous close."""
    if previous_close is None or previous_close <= 0:
        return None
    return abs(close - previous_close) / previous_close * _PCT


def assess_signal(
    signal: Signal,
    portfolio: PortfolioState,
    price: Decimal,
    market: MarketInfo,
    *,
    fee_rate: Decimal,
    slippage_bps: Decimal,
    limits: RiskLimits,
    kill_switch_active: bool,
    candle_range: Decimal = Decimal(0),
    global_limits: GlobalRiskLimits | None = None,
    exposure: GlobalExposure | None = None,
    avg_quote_volume: Decimal | None = None,
    close_jump: Decimal | None = None,
) -> RiskDecision:
    """Approve and size a signal, or reject it with a reason.

    The kill switch and every entry check block new positions only: exits stay allowed
    because they reduce risk.
    """
    global_limits = global_limits or GlobalRiskLimits()
    exposure = exposure or GlobalExposure()
    if signal.side is Side.SELL:
        return _assess_exit(portfolio, price, market, slippage_bps)

    if kill_switch_active:
        return RiskDecision.reject("kill switch is active")
    if portfolio.quantity > 0:
        return RiskDecision.reject("already in position")
    if limits.max_candle_range_pct is not None and candle_range > limits.max_candle_range_pct:
        return RiskDecision.reject(
            f"candle range {candle_range:.1f}% exceeds "
            f"{limits.max_candle_range_pct}% (suspect data)"
        )
    if (
        limits.max_close_jump_pct is not None
        and close_jump is not None
        and close_jump > limits.max_close_jump_pct
    ):
        return RiskDecision.reject(
            f"close moved {close_jump:.1f}% from the previous close, above "
            f"{limits.max_close_jump_pct}% (suspect data)"
        )
    if limits.require_stop_loss and signal.stop_loss is None:
        return RiskDecision.reject("a stop-loss is required but the signal has none")
    if signal.stop_loss is not None and signal.stop_loss >= price:
        return RiskDecision.reject("stop-loss must be below the entry price")
    if signal.take_profit is not None and signal.take_profit <= price:
        return RiskDecision.reject("take-profit must be above the entry price")
    if (
        global_limits.max_open_positions is not None
        and exposure.open_positions >= global_limits.max_open_positions
    ):
        return RiskDecision.reject("global limit of open positions reached")

    entry = slipped_price(Side.BUY, price, slippage_bps)
    equity = portfolio.equity(price)
    budget = min(portfolio.available_cash, equity * limits.max_position_fraction)
    if limits.max_order_notional is not None:
        budget = min(budget, limits.max_order_notional)
    if limits.max_risk_per_trade_pct is not None and signal.stop_loss is not None:
        # Size so that being stopped out loses at most the configured share of equity.
        quantity_at_risk = (
            equity * limits.max_risk_per_trade_pct / _PCT / (entry - signal.stop_loss)
        )
        budget = min(budget, quantity_at_risk * entry * (1 + fee_rate))
    if limits.max_order_pct_of_volume is not None and avg_quote_volume is not None:
        budget = min(budget, avg_quote_volume * limits.max_order_pct_of_volume / _PCT)
    if global_limits.max_total_exposure is not None:
        remaining = global_limits.max_total_exposure - exposure.notional
        if remaining <= 0:
            return RiskDecision.reject("global exposure limit reached")
        budget = min(budget, remaining)

    try:
        quantity = affordable_buy_quantity(budget, entry, fee_rate, market)
    except OrderRejected as exc:
        if limits.max_order_pct_of_volume is not None and avg_quote_volume is not None:
            return RiskDecision.reject(
                f"{exc} after capping the order at {limits.max_order_pct_of_volume}% of the "
                f"average volume ({avg_quote_volume:.2f} quote)"
            )
        return RiskDecision.reject(str(exc))
    return RiskDecision(approved=True, quantity=quantity)


MIN_VOLUME_SAMPLES = 5  # with fewer recent candles the average volume is not trusted


def average_quote_volume(quote_volumes: Sequence[Decimal]) -> Decimal | None:
    """Average traded value (volume x close) of the recent candles, or None if too few."""
    if len(quote_volumes) < MIN_VOLUME_SAMPLES:
        return None
    return sum(quote_volumes, Decimal(0)) / len(quote_volumes)


def _assess_exit(
    portfolio: PortfolioState, price: Decimal, market: MarketInfo, slippage_bps: Decimal
) -> RiskDecision:
    if portfolio.available_quantity <= 0:
        return RiskDecision.reject("no position to sell")
    try:
        quantity = normalize_quantity(
            portfolio.available_quantity, slipped_price(Side.SELL, price, slippage_bps), market
        )
    except OrderRejected as exc:
        return RiskDecision.reject(str(exc))
    return RiskDecision(approved=True, quantity=quantity)


def daily_loss_breached(equity: Decimal, day_start_equity: Decimal, limits: RiskLimits) -> bool:
    if limits.max_daily_loss_pct is None or day_start_equity <= 0:
        return False
    return (day_start_equity - equity) / day_start_equity * _PCT >= limits.max_daily_loss_pct


def drawdown_breached(equity: Decimal, peak_equity: Decimal, limits: RiskLimits) -> bool:
    if limits.max_drawdown_pct is None or peak_equity <= 0:
        return False
    return (peak_equity - equity) / peak_equity * _PCT >= limits.max_drawdown_pct


def consecutive_losses_breached(round_trip_pnls: Sequence[Decimal], limits: RiskLimits) -> bool:
    n = limits.max_consecutive_losses
    if n is None or len(round_trip_pnls) < n:
        return False
    return all(pnl < 0 for pnl in round_trip_pnls[-n:])


_LIMIT_DECIMALS = (
    "max_position_fraction",
    "max_order_notional",
    "max_daily_loss_pct",
    "max_drawdown_pct",
    "max_risk_per_trade_pct",
    "max_candle_range_pct",
    "max_order_pct_of_volume",
    "max_close_jump_pct",
)


def limits_to_dict(limits: RiskLimits) -> dict[str, object]:
    out: dict[str, object] = {
        name: None if getattr(limits, name) is None else str(getattr(limits, name))
        for name in _LIMIT_DECIMALS
    }
    out["max_consecutive_losses"] = limits.max_consecutive_losses
    out["require_stop_loss"] = limits.require_stop_loss
    out["drawdown_action"] = limits.drawdown_action.value
    return out


def limits_from_dict(raw: dict[str, object]) -> RiskLimits:
    values: dict[str, object] = {
        name: None if raw.get(name) is None else Decimal(str(raw[name]))
        for name in _LIMIT_DECIMALS
        if name in raw
    }
    if raw.get("max_consecutive_losses") is not None:
        values["max_consecutive_losses"] = int(str(raw["max_consecutive_losses"]))
    values["require_stop_loss"] = bool(raw.get("require_stop_loss", False))
    values["drawdown_action"] = DrawdownAction(str(raw.get("drawdown_action", "pause")))
    return RiskLimits(**values)  # type: ignore[arg-type]
