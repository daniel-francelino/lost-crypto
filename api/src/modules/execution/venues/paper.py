"""Paper venue: implements ``ExchangeGateway`` with simulated fills at real market prices.

It is the reference implementation of the gateway contract; a testnet or live adapter is a
drop-in replacement because callers only see the port.
"""

from datetime import datetime
from decimal import Decimal
from typing import Protocol

from modules.exchanges.application.ports import MarketOrderRequest, VenueOrder
from modules.exchanges.domain.models import ExchangeCapabilities
from modules.exchanges.errors import ExchangeRejected, UnknownOrder
from modules.execution.domain.fills import simulate_market_fill
from modules.execution.domain.normalizer import OrderRejected
from modules.execution.domain.orders import OrderStatus
from modules.market_data.domain.models import MarketInfo


class PriceFeed(Protocol):
    """The price a market order executes against (the simulator has no order book)."""

    def last_price(self, symbol: str) -> tuple[Decimal, datetime]: ...


class MarketRules(Protocol):
    async def fetch_market_info(self, symbol: str) -> MarketInfo: ...


class StaticPriceFeed:
    """Prices set explicitly by the caller (e.g. the close of the candle being processed)."""

    def __init__(self) -> None:
        self._prices: dict[str, tuple[Decimal, datetime]] = {}

    def set(self, symbol: str, price: Decimal, at: datetime) -> None:
        self._prices[symbol] = (price, at)

    def last_price(self, symbol: str) -> tuple[Decimal, datetime]:
        try:
            return self._prices[symbol]
        except KeyError:
            raise ExchangeRejected(f"no price available for {symbol}") from None


class PaperExchangeGateway:
    def __init__(
        self,
        capabilities: ExchangeCapabilities,
        rules: MarketRules,
        prices: PriceFeed,
        fee_rate: Decimal,
        slippage_bps: Decimal,
    ) -> None:
        self._capabilities = capabilities
        self._rules = rules
        self._prices = prices
        self._fee_rate = fee_rate
        self._slippage_bps = slippage_bps
        self._orders: dict[str, VenueOrder] = {}

    @property
    def capabilities(self) -> ExchangeCapabilities:
        return self._capabilities

    async def create_market_order(self, request: MarketOrderRequest) -> VenueOrder:
        if len(request.client_order_id) > self._capabilities.max_client_order_id_length:
            raise ExchangeRejected(
                f"client order id longer than {self._capabilities.max_client_order_id_length}"
            )
        existing = self._orders.get(request.client_order_id)
        if existing is not None:  # idempotent: never a second order for the same id
            return existing

        market = await self._rules.fetch_market_info(request.symbol)
        price, at = self._prices.last_price(request.symbol)
        try:
            fill = simulate_market_fill(
                request.side,
                request.quantity,
                price,
                self._fee_rate,
                self._slippage_bps,
                market,
                at,
            )
        except OrderRejected as exc:
            raise ExchangeRejected(str(exc)) from exc

        order = VenueOrder(
            client_order_id=request.client_order_id,
            exchange_order_id=f"paper-{request.client_order_id}",
            symbol=request.symbol,
            side=request.side,
            quantity=fill.quantity,
            status=OrderStatus.FILLED,
            filled_quantity=fill.quantity,
            fills=(fill,),
        )
        self._orders[request.client_order_id] = order
        return order

    async def fetch_order(self, symbol: str, client_order_id: str) -> VenueOrder | None:
        order = self._orders.get(client_order_id)
        return order if order is not None and order.symbol == symbol else None

    async def cancel_order(self, symbol: str, client_order_id: str) -> VenueOrder:
        order = await self.fetch_order(symbol, client_order_id)
        if order is None:
            raise UnknownOrder(client_order_id)
        raise ExchangeRejected("order is already filled")  # market orders fill immediately
