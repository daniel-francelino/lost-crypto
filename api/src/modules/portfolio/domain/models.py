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
    cash: Decimal  # all quote currency the bot owns, reserved included
    quantity: Decimal = Decimal(0)
    avg_entry_price: Decimal = Decimal(0)
    realized_pnl: Decimal = Decimal(0)
    fees_paid: Decimal = Decimal(0)
    # Protective levels of the open position (cleared when it is closed).
    stop_price: Decimal | None = None
    take_profit_price: Decimal | None = None
    # Capital promised to orders still in flight on an exchange (not spendable twice).
    reserved_cash: Decimal = Decimal(0)
    reserved_quantity: Decimal = Decimal(0)
    # Client id of the stop-loss resting on the exchange, when one protects the position.
    stop_order_client_id: str | None = None

    @classmethod
    def new(cls, bot_id: UUID, initial_capital: Decimal) -> "PortfolioState":
        return cls(bot_id=bot_id, cash=initial_capital)

    @property
    def available_cash(self) -> Decimal:
        return self.cash - self.reserved_cash

    @property
    def available_quantity(self) -> Decimal:
        return self.quantity - self.reserved_quantity

    def equity(self, price: Decimal) -> Decimal:
        return self.cash + self.quantity * price

    def reserve(self, cash: Decimal = Decimal(0), quantity: Decimal = Decimal(0)) -> None:
        if cash > self.available_cash or quantity > self.available_quantity:
            raise InsufficientFunds("not enough unreserved balance for this order")
        self.reserved_cash += cash
        self.reserved_quantity += quantity

    def release(self, cash: Decimal = Decimal(0), quantity: Decimal = Decimal(0)) -> None:
        self.reserved_cash = max(Decimal(0), self.reserved_cash - cash)
        self.reserved_quantity = max(Decimal(0), self.reserved_quantity - quantity)

    def write_off_dust(self, min_quantity: Decimal) -> Decimal:
        """Treat a leftover below the exchange's minimum tradable size as flat.

        A base-asset fee leaves crumbs (e.g. 0.0009 BTC) that can never be sold; keeping them
        as an "open position" would block the bot forever. The crumbs' cost is written off
        against realised PnL. Returns the quantity written off.
        """
        if self.quantity <= 0 or self.quantity >= min_quantity:
            return Decimal(0)
        dust = self.quantity
        self.realized_pnl -= self.avg_entry_price * dust
        self.quantity = Decimal(0)
        self.avg_entry_price = Decimal(0)
        self.stop_price = self.take_profit_price = self.stop_order_client_id = None
        return dust

    def apply_fill(self, fill: Fill) -> None:
        if fill.side is Side.BUY:
            cost = fill.notional + fill.fee  # quote actually spent
            if cost > self.cash:
                raise InsufficientFunds(f"cost {cost} exceeds cash {self.cash}")
            # A fee charged in the base asset reduces what is received; its value is still a
            # cost of the position.
            received = fill.quantity - fill.fee_base
            basis = self.avg_entry_price * self.quantity + cost + fill.fee_base * fill.price
            self.quantity += received
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
                self.stop_order_client_id = None
        self.fees_paid += fill.total_fee


@dataclass(frozen=True, slots=True)
class PortfolioSnapshot:
    bot_id: UUID
    session_id: UUID
    taken_at: datetime
    price: Decimal
    cash: Decimal
    quantity: Decimal
    equity: Decimal
