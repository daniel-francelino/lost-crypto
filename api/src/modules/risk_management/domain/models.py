"""Risk rules as pure functions: every signal goes through ``assess_signal`` before an order."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from core.errors import DomainError
from modules.execution.domain.fills import affordable_buy_quantity, slipped_price
from modules.execution.domain.normalizer import OrderRejected, normalize_quantity
from modules.market_data.domain.models import MarketInfo
from modules.portfolio.domain.models import PortfolioState
from modules.strategies.domain.types import Side, Signal

_PCT = Decimal(100)


class InvalidRiskLimits(DomainError):
    pass


@dataclass(frozen=True, slots=True)
class RiskLimits:
    max_position_fraction: Decimal = Decimal(1)  # share of equity a position may use (0, 1]
    max_order_notional: Decimal | None = None  # hard cap per order, in quote currency
    max_daily_loss_pct: Decimal | None = Decimal(10)  # pause the bot beyond this loss in a UTC day

    def __post_init__(self) -> None:
        if not (0 < self.max_position_fraction <= 1):
            raise InvalidRiskLimits("max_position_fraction must be in (0, 1]")
        if self.max_order_notional is not None and self.max_order_notional <= 0:
            raise InvalidRiskLimits("max_order_notional must be positive")
        if self.max_daily_loss_pct is not None and not (0 < self.max_daily_loss_pct <= 100):
            raise InvalidRiskLimits("max_daily_loss_pct must be in (0, 100]")


@dataclass(frozen=True, slots=True)
class RiskDecision:
    approved: bool
    quantity: Decimal | None = None
    reason: str | None = None

    @classmethod
    def reject(cls, reason: str) -> "RiskDecision":
        return cls(approved=False, reason=reason)


@dataclass(frozen=True, slots=True)
class KillSwitchState:
    active: bool = False
    reason: str | None = None
    changed_at: datetime | None = None


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
) -> RiskDecision:
    """Approve and size a signal, or reject it with a reason.

    The kill switch blocks new entries only: exits stay allowed because they reduce risk.
    """
    if signal.side is Side.BUY:
        if kill_switch_active:
            return RiskDecision.reject("kill switch is active")
        if portfolio.quantity > 0:
            return RiskDecision.reject("already in position")
        budget = min(portfolio.cash, portfolio.equity(price) * limits.max_position_fraction)
        if limits.max_order_notional is not None:
            budget = min(budget, limits.max_order_notional)
        try:
            quantity = affordable_buy_quantity(
                budget, slipped_price(Side.BUY, price, slippage_bps), fee_rate, market
            )
        except OrderRejected as exc:
            return RiskDecision.reject(str(exc))
        return RiskDecision(approved=True, quantity=quantity)

    if portfolio.quantity <= 0:
        return RiskDecision.reject("no position to sell")
    try:
        quantity = normalize_quantity(
            portfolio.quantity, slipped_price(Side.SELL, price, slippage_bps), market
        )
    except OrderRejected as exc:
        return RiskDecision.reject(str(exc))
    return RiskDecision(approved=True, quantity=quantity)


def daily_loss_breached(equity: Decimal, day_start_equity: Decimal, limits: RiskLimits) -> bool:
    if limits.max_daily_loss_pct is None or day_start_equity <= 0:
        return False
    loss_pct = (day_start_equity - equity) / day_start_equity * _PCT
    return loss_pct >= limits.max_daily_loss_pct
