from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from core.errors import DomainError
from modules.execution.domain.orders import Fill
from modules.strategies.domain.types import Side


class InsufficientFunds(DomainError):
    pass


@dataclass(slots=True)
class PortfolioState:
    """Virtual single-symbol spot portfolio of one bot (quote currency cash + base position).

    ``avg_entry_price`` is the cost basis per unit *including the buy fee*, so
    ``realized_pnl`` is net of both fees. ``fees_paid`` is tracked separately.
    """

    bot_id: UUID
    cash: Decimal
    quantity: Decimal = Decimal(0)
    avg_entry_price: Decimal = Decimal(0)
    realized_pnl: Decimal = Decimal(0)
    fees_paid: Decimal = Decimal(0)
    # Protective levels of the open position (cleared when it is closed).
    stop_price: Decimal | None = None
    take_profit_price: Decimal | None = None

    @classmethod
    def new(cls, bot_id: UUID, initial_capital: Decimal) -> "PortfolioState":
        return cls(bot_id=bot_id, cash=initial_capital)

    def equity(self, price: Decimal) -> Decimal:
        return self.cash + self.quantity * price

    def apply_fill(self, fill: Fill) -> None:
        if fill.side is Side.BUY:
            cost = fill.notional + fill.fee
            if cost > self.cash:
                raise InsufficientFunds(f"cost {cost} exceeds cash {self.cash}")
            basis = self.avg_entry_price * self.quantity + cost
            self.quantity += fill.quantity
            self.avg_entry_price = basis / self.quantity
            self.cash -= cost
        else:
            if fill.quantity > self.quantity:
                raise InsufficientFunds(f"sell {fill.quantity} exceeds position {self.quantity}")
            self.realized_pnl += (fill.notional - fill.fee) - self.avg_entry_price * fill.quantity
            self.quantity -= fill.quantity
            self.cash += fill.notional - fill.fee
            if self.quantity == 0:
                self.avg_entry_price = Decimal(0)
                self.stop_price = None
                self.take_profit_price = None
        self.fees_paid += fill.fee


@dataclass(frozen=True, slots=True)
class PortfolioSnapshot:
    bot_id: UUID
    session_id: UUID
    taken_at: datetime
    price: Decimal
    cash: Decimal
    quantity: Decimal
    equity: Decimal
