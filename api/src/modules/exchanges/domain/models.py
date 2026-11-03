"""What the rest of the system may know about an exchange: static facts, never SDK details."""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from core.errors import DomainError
from modules.market_data.domain.models import Timeframe

MAX_PERPETUAL_LEVERAGE = 10


class TradingProduct(StrEnum):
    SPOT = "spot"
    LINEAR_PERPETUAL = "linear_perpetual"


class PositionSide(StrEnum):
    LONG = "long"
    SHORT = "short"


class MarginMode(StrEnum):
    ISOLATED = "isolated"


@dataclass(frozen=True, slots=True)
class LeverageTier:
    """Venue-reported notional bracket for a linear contract."""

    tier: int
    min_notional: Decimal
    max_notional: Decimal
    max_leverage: int
    maintenance_margin_rate: Decimal
    cumulative_maintenance_amount: Decimal = Decimal(0)

    def __post_init__(self) -> None:
        if (
            self.tier < 1
            or self.min_notional < 0
            or self.max_notional <= self.min_notional
            or self.max_leverage < 1
            or not 0 <= self.maintenance_margin_rate < 1
            or self.cumulative_maintenance_amount < 0
        ):
            raise ValueError("exchange returned an invalid leverage tier")

    def supports(self, notional: Decimal, leverage: int) -> bool:
        return (
            self.min_notional <= notional < self.max_notional and 1 <= leverage <= self.max_leverage
        )


class OrderType(StrEnum):
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"


@dataclass(frozen=True, slots=True)
class ExchangeCapabilities:
    """Declared by each exchange profile; callers branch on these, never on the exchange name."""

    exchange_id: str
    name: str
    order_types: frozenset[OrderType]
    native_stop_orders: bool  # stops live on the exchange and survive a worker outage
    max_client_order_id_length: int
    has_testnet: bool
    timeframes: frozenset[Timeframe]
    products: frozenset[TradingProduct] = frozenset({TradingProduct.SPOT})
    max_leverage: int = 1
    has_demo: bool = False

    def __post_init__(self) -> None:
        if not self.products:
            raise ValueError("an exchange must support at least one trading product")
        if not 1 <= self.max_leverage <= MAX_PERPETUAL_LEVERAGE:
            raise ValueError(f"max_leverage must be between 1 and {MAX_PERPETUAL_LEVERAGE}")
        if TradingProduct.LINEAR_PERPETUAL not in self.products and self.max_leverage != 1:
            raise ValueError("leverage is only valid for linear perpetual markets")


class InvalidFeeSchedule(DomainError):
    pass


@dataclass(frozen=True, slots=True)
class FeeSchedule:
    """Default fee rates (fractions of notional). Market orders are takers."""

    maker_rate: Decimal
    taker_rate: Decimal

    def __post_init__(self) -> None:
        if not (0 <= self.maker_rate < 1 and 0 <= self.taker_rate < 1):
            raise InvalidFeeSchedule("fee rates must be in [0, 1)")


@dataclass(frozen=True, slots=True)
class ExchangeProfile:
    capabilities: ExchangeCapabilities
    fees: FeeSchedule

    @property
    def exchange_id(self) -> str:
        return self.capabilities.exchange_id
