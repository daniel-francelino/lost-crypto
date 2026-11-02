from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from modules.exchanges.domain.models import (
    MAX_PERPETUAL_LEVERAGE,
    ExchangeCapabilities,
    MarginMode,
    PositionSide,
    TradingProduct,
)
from modules.execution.domain.orders import Fill, OrderStatus
from modules.strategies.domain.types import Side


@dataclass(frozen=True, slots=True)
class MarketOrderRequest:
    client_order_id: str
    symbol: str
    side: Side
    quantity: Decimal
    product: TradingProduct = TradingProduct.SPOT
    position_side: PositionSide | None = None
    leverage: int = 1
    margin_mode: MarginMode = MarginMode.ISOLATED
    reduce_only: bool = False

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValueError("order quantity must be positive")
        if self.product is TradingProduct.SPOT:
            if self.position_side is not None or self.leverage != 1 or self.reduce_only:
                raise ValueError("spot orders cannot set position side, leverage or reduce-only")
            return
        if self.position_side is None:
            raise ValueError("perpetual orders must specify long or short position side")
        if self.margin_mode is not MarginMode.ISOLATED:
            raise ValueError("perpetual orders currently require isolated margin")
        if not 1 <= self.leverage <= MAX_PERPETUAL_LEVERAGE:
            raise ValueError(f"perpetual leverage must be between 1x and {MAX_PERPETUAL_LEVERAGE}x")
        expected_side = (
            (Side.SELL if self.position_side is PositionSide.LONG else Side.BUY)
            if self.reduce_only
            else (Side.BUY if self.position_side is PositionSide.LONG else Side.SELL)
        )
        if self.side is not expected_side:
            action = "reduce" if self.reduce_only else "open"
            raise ValueError(
                f"{self.side.value} cannot {action} a {self.position_side.value} position"
            )


@dataclass(frozen=True, slots=True)
class StopOrderRequest:
    """A protective stop-market order, optionally reducing one perpetual position."""

    client_order_id: str
    symbol: str
    quantity: Decimal
    stop_price: Decimal
    side: Side = Side.SELL
    product: TradingProduct = TradingProduct.SPOT
    position_side: PositionSide | None = None
    reduce_only: bool = False

    def __post_init__(self) -> None:
        if self.quantity <= 0 or self.stop_price <= 0:
            raise ValueError("stop quantity and trigger price must be positive")
        if self.product is TradingProduct.SPOT:
            if self.side is not Side.SELL or self.position_side is not None or self.reduce_only:
                raise ValueError("spot protective stops must be sell orders without position flags")
            return
        if self.position_side is None or not self.reduce_only:
            raise ValueError("perpetual protective stops must identify and reduce a position")
        expected_side = Side.SELL if self.position_side is PositionSide.LONG else Side.BUY
        if self.side is not expected_side:
            raise ValueError("perpetual protective stop side must reduce its position")


@dataclass(frozen=True, slots=True)
class Balance:
    asset: str
    free: Decimal
    locked: Decimal

    @property
    def total(self) -> Decimal:
        return self.free + self.locked


@dataclass(frozen=True, slots=True)
class VenueOrder:
    """An order as the venue reports it."""

    client_order_id: str
    exchange_order_id: str | None
    symbol: str
    side: Side
    quantity: Decimal
    status: OrderStatus
    filled_quantity: Decimal
    fills: tuple[Fill, ...]
    order_type: str = "market"  # market | stop_loss
    stop_price: Decimal | None = None


class ExchangeGateway(Protocol):
    """Order operations against one venue (paper simulator, testnet or live exchange).

    Contract every implementation must honour (see tests/contract):
    * ``create_market_order`` is idempotent on ``client_order_id``: repeating it returns the
      existing order and never places a second one;
    * quantities are validated against the venue's rules and refused with ``ExchangeRejected``;
    * ``fetch_order`` returns None for an unknown id, ``cancel_order`` raises ``UnknownOrder``.
    The strategy and risk layers only ever see this port, so swapping venue or exchange never
    touches them.
    """

    @property
    def capabilities(self) -> ExchangeCapabilities: ...

    async def create_market_order(self, request: MarketOrderRequest) -> VenueOrder: ...
    async def fetch_order(self, symbol: str, client_order_id: str) -> VenueOrder | None: ...
    async def cancel_order(self, symbol: str, client_order_id: str) -> VenueOrder: ...
