from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Any, Protocol

from modules.market_data.domain.models import Candle


class Side(StrEnum):
    BUY = "buy"
    SELL = "sell"


class SignalKind(StrEnum):
    ENTRY = "entry"
    EXIT = "exit"


@dataclass(frozen=True, slots=True)
class Signal:
    """A strategy's *intent*. It is not an order: sizing, risk and execution decide the rest."""

    side: Side
    symbol: str
    kind: SignalKind
    reason: str
    # Protective levels a strategy may propose with an entry (price levels, quote currency).
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None


@dataclass(frozen=True, slots=True)
class StrategyContext:
    """Read-only view handed to a strategy for one *closed* candle."""

    symbol: str
    candle: Candle
    position_quantity: Decimal


@dataclass(frozen=True, slots=True)
class StrategyResult[StateT]:
    signals: tuple[Signal, ...]
    state: StateT


class Strategy[StateT](Protocol):
    """Pure algorithm: no I/O, no clock, no persistence. State is explicit and returned."""

    def initial_state(self) -> StateT: ...

    def evaluate(self, ctx: StrategyContext, state: StateT) -> StrategyResult[StateT]: ...

    def serialize_state(self, state: StateT) -> dict[str, Any]:
        """JSON-compatible form, so a bot can resume after a restart."""
        ...

    def deserialize_state(self, raw: dict[str, Any]) -> StateT: ...
