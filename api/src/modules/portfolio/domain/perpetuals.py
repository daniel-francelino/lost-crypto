"""Pure accounting primitives for linear, quote-margined perpetual positions.

These value objects are deliberately separate from the existing spot portfolio. A futures
position has margin and signed directional PnL; it must never be represented as owned base-asset
quantity or treated as spot cash.
"""

from dataclasses import dataclass
from decimal import Decimal

from core.errors import DomainError
from modules.exchanges.domain.models import MAX_PERPETUAL_LEVERAGE, PositionSide


class InvalidPerpetualPosition(DomainError):
    pass


@dataclass(frozen=True, slots=True)
class LinearPerpetualPosition:
    side: PositionSide
    quantity: Decimal
    entry_price: Decimal
    leverage: int
    isolated_margin: Decimal

    def __post_init__(self) -> None:
        if self.quantity <= 0 or self.entry_price <= 0 or self.isolated_margin <= 0:
            raise InvalidPerpetualPosition("quantity, entry price and margin must be positive")
        if not 1 <= self.leverage <= MAX_PERPETUAL_LEVERAGE:
            raise InvalidPerpetualPosition(
                f"leverage must be between 1x and {MAX_PERPETUAL_LEVERAGE}x"
            )
        required_margin = self.notional / self.leverage
        if self.isolated_margin < required_margin:
            raise InvalidPerpetualPosition(
                f"isolated margin {self.isolated_margin} is below required {required_margin}"
            )

    @property
    def notional(self) -> Decimal:
        return self.quantity * self.entry_price

    @property
    def initial_margin(self) -> Decimal:
        return self.notional / self.leverage

    def unrealized_pnl(self, mark_price: Decimal) -> Decimal:
        if mark_price <= 0:
            raise InvalidPerpetualPosition("mark price must be positive")
        move = mark_price - self.entry_price
        return move * self.quantity * (1 if self.side is PositionSide.LONG else -1)

    def funding_pnl(self, mark_price: Decimal, funding_rate: Decimal) -> Decimal:
        """Net account change at a funding event; positive rate means longs pay shorts."""
        if mark_price <= 0:
            raise InvalidPerpetualPosition("mark price must be positive")
        payment = mark_price * self.quantity * funding_rate
        return -payment if self.side is PositionSide.LONG else payment

    def estimated_liquidation_price(self, maintenance_margin_rate: Decimal) -> Decimal:
        """Fee-free isolated-margin estimate; venue-specific liquidation rules still govern."""
        if not 0 <= maintenance_margin_rate < 1:
            raise InvalidPerpetualPosition("maintenance margin rate must be in [0, 1)")
        margin_per_unit = self.isolated_margin / self.quantity
        if self.side is PositionSide.LONG:
            return (self.entry_price - margin_per_unit) / (1 - maintenance_margin_rate)
        return (self.entry_price + margin_per_unit) / (1 + maintenance_margin_rate)
