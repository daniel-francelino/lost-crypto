import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from core.errors import ConflictError
from modules.strategies.domain.types import Side


class OrderStatus(StrEnum):
    INTENT = "INTENT"  # persisted before any venue call (write-ahead)
    SUBMITTING = "SUBMITTING"
    OPEN = "OPEN"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    UNKNOWN = "UNKNOWN"  # outcome uncertain (timeout): resolved only by reconciliation


# Transitions only move forward; terminal states have no way out.
_ALLOWED: dict[OrderStatus, frozenset[OrderStatus]] = {
    OrderStatus.INTENT: frozenset({OrderStatus.SUBMITTING, OrderStatus.REJECTED}),
    OrderStatus.SUBMITTING: frozenset(
        {
            OrderStatus.OPEN,
            OrderStatus.PARTIALLY_FILLED,
            OrderStatus.FILLED,
            OrderStatus.REJECTED,
            OrderStatus.UNKNOWN,
        }
    ),
    OrderStatus.UNKNOWN: frozenset({OrderStatus.OPEN, OrderStatus.FILLED, OrderStatus.REJECTED}),
    OrderStatus.OPEN: frozenset(
        {
            OrderStatus.PARTIALLY_FILLED,
            OrderStatus.FILLED,
            OrderStatus.CANCELED,
            OrderStatus.EXPIRED,
        }
    ),
    OrderStatus.PARTIALLY_FILLED: frozenset(
        {OrderStatus.PARTIALLY_FILLED, OrderStatus.FILLED, OrderStatus.CANCELED}
    ),
    OrderStatus.FILLED: frozenset(),
    OrderStatus.CANCELED: frozenset(),
    OrderStatus.REJECTED: frozenset(),
    OrderStatus.EXPIRED: frozenset(),
}


class InvalidOrderTransition(ConflictError):
    pass


@dataclass(frozen=True, slots=True)
class Fill:
    time: datetime
    side: Side
    quantity: Decimal
    price: Decimal
    fee: Decimal

    @property
    def notional(self) -> Decimal:
        return self.quantity * self.price


@dataclass(slots=True)
class Order:
    """Market order of a bot. ``client_order_id`` is deterministic, so processing the same
    candle twice yields the same id and the unique constraint turns it into a no-op."""

    id: UUID
    bot_id: UUID
    session_id: UUID
    client_order_id: str
    symbol: str
    side: Side
    quantity: Decimal
    bar_time: datetime
    created_at: datetime
    status: OrderStatus = OrderStatus.INTENT
    filled_quantity: Decimal = Decimal(0)
    avg_fill_price: Decimal | None = None
    reject_reason: str | None = None
    fills: list[Fill] = field(default_factory=list)

    def transition(self, new: OrderStatus) -> None:
        if new not in _ALLOWED[self.status]:
            raise InvalidOrderTransition(f"{self.status} -> {new} is not allowed")
        self.status = new

    def submit(self) -> None:
        self.transition(OrderStatus.SUBMITTING)

    def reject(self, reason: str) -> None:
        self.transition(OrderStatus.REJECTED)
        self.reject_reason = reason

    def apply_fill(self, fill: Fill) -> None:
        if self.filled_quantity + fill.quantity > self.quantity:
            raise InvalidOrderTransition("fill exceeds the order quantity")
        previous_value = (self.avg_fill_price or Decimal(0)) * self.filled_quantity
        self.fills.append(fill)
        self.filled_quantity += fill.quantity
        self.avg_fill_price = (previous_value + fill.notional) / self.filled_quantity
        done = self.filled_quantity == self.quantity
        self.transition(OrderStatus.FILLED if done else OrderStatus.PARTIALLY_FILLED)


def make_client_order_id(bot_id: UUID, bar_time: datetime, side: Side) -> str:
    """Deterministic per (bot, candle, side): the same decision always maps to the same id."""
    digest = hashlib.sha256(f"{bot_id}|{bar_time.isoformat()}|{side.value}".encode()).hexdigest()
    return f"lc-{digest[:32]}"
