from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from modules.exchanges.domain.models import PositionSide
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
    # Fraction of the currently open position to close; omitted means a full exit.
    exit_fraction: Decimal | None = None

    def __post_init__(self) -> None:
        if self.exit_fraction is not None and (
            self.kind is not SignalKind.EXIT
            or not self.exit_fraction.is_finite()
            or not 0 < self.exit_fraction <= 1
        ):
            raise ValueError("exit_fraction must be in (0, 1] and only applies to exit signals")


@dataclass(frozen=True, slots=True)
class StrategyContext:
    """Read-only view handed to a strategy for one *closed* candle."""

    symbol: str
    candle: Candle
    position_quantity: Decimal
    position_side: PositionSide | None = None
    allow_short: bool = False

    @property
    def is_long(self) -> bool:
        return self.position_quantity > 0 and self.position_side is not PositionSide.SHORT

    @property
    def is_short(self) -> bool:
        return self.position_quantity > 0 and self.position_side is PositionSide.SHORT

    @property
    def is_flat(self) -> bool:
        return self.position_quantity <= 0


@dataclass(frozen=True, slots=True)
class StrategyResult[StateT]:
    signals: tuple[Signal, ...]
    state: StateT
