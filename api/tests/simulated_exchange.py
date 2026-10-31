"""A simulated exchange account that honours the ``Exchange`` contract, for integration tests.

It behaves like a spot venue: balances, idempotent client order ids, fees charged the way
Binance charges them (buys pay the fee in the base asset, sells in the quote asset), resting
stop orders that fire when the market falls through them, and failure injection so tests can
reproduce timeouts, rejections, bad credentials and rate limits deterministically.
"""

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Protocol

from factories import MARKET
from modules.exchanges.application.exchange import Exchange
from modules.exchanges.application.ports import (
    Balance,
    MarketOrderRequest,
    StopOrderRequest,
    VenueOrder,
)
from modules.exchanges.errors import (
    AuthenticationFailed,
    ExchangeRejected,
    TransientExchangeError,
    UnknownOrder,
    UnknownOutcome,
)
from modules.exchanges.infrastructure.binance import BINANCE_PROFILE
from modules.execution.domain.orders import Fill, OrderStatus
from modules.market_data.domain.models import Candle, MarketInfo, Timeframe
from modules.strategies.domain.types import Side


class Clock(Protocol):
    def now(self) -> datetime: ...


class CandleSource(Protocol):
    async def fetch_candles(
        self, symbol: str, timeframe: Timeframe, since: datetime, limit: int
    ) -> list[Candle]: ...
    async def fetch_market_info(self, symbol: str) -> MarketInfo: ...


class PriceFn(Protocol):
    def __call__(self, symbol: str) -> Decimal: ...


@dataclass
class SimOrder:
    client_order_id: str
    exchange_order_id: str
    symbol: str
    side: Side
    quantity: Decimal
    order_type: str
    status: OrderStatus
    stop_price: Decimal | None = None
    fills: list[Fill] = field(default_factory=list)

    @property
    def filled(self) -> Decimal:
        return sum((f.quantity for f in self.fills), Decimal(0))

    def to_venue(self) -> VenueOrder:
        return VenueOrder(
            client_order_id=self.client_order_id,
            exchange_order_id=self.exchange_order_id,
            symbol=self.symbol,
            side=self.side,
            quantity=self.quantity,
            status=self.status,
            filled_quantity=self.filled,
            fills=tuple(self.fills),
            order_type=self.order_type,
            stop_price=self.stop_price,
        )


class SimulatedExchange(Exchange):
    PROFILE = BINANCE_PROFILE

    def __init__(
        self,
        source: CandleSource,
        clock: Clock,
        price_fn: PriceFn,
        balances: dict[str, Decimal],
        fee_rate: Decimal = Decimal("0.001"),
    ) -> None:
        self.source = source
        self.clock = clock
        self.price_fn = price_fn
        self.balances = dict(balances)
        self.fee_rate = fee_rate
        self.orders: dict[str, SimOrder] = {}
        self.create_calls: list[str] = []  # every create attempt, by client order id
        self.cancel_calls: list[str] = []
        self._failures: dict[str, deque[str]] = {}
        self._trade_seq = 0

    # --- test controls -----------------------------------------------------------------------

    def fail_next(self, operation: str, mode: str) -> None:
        """operation: create | create_stop | cancel; mode: reject | timeout_before |
        timeout_after | auth | rate_limit."""
        self._failures.setdefault(operation, deque()).append(mode)

    def tick(self) -> None:
        """Let resting stop orders react to the current market price."""
        for order in self.orders.values():
            if order.status is OrderStatus.OPEN and order.stop_price is not None:
                price = self.price_fn(order.symbol)
                if price <= order.stop_price:
                    self._execute(order, price)

    def open_orders(self) -> list[SimOrder]:
        return [o for o in self.orders.values() if o.status is OrderStatus.OPEN]

    def place_foreign_order(self, client_order_id: str, symbol: str = "TST/USDT") -> None:
        """An open order we did not place (or one carrying our prefix but unknown to us)."""
        self.orders[client_order_id] = SimOrder(
            client_order_id,
            f"X{len(self.orders)}",
            symbol,
            Side.SELL,
            Decimal(1),
            "limit",
            OrderStatus.OPEN,
        )

    # --- market data -------------------------------------------------------------------------

    async def fetch_candles(
        self, symbol: str, timeframe: Timeframe, since: datetime, limit: int
    ) -> list[Candle]:
        return await self.source.fetch_candles(symbol, timeframe, since, limit)

    async def fetch_market_info(self, symbol: str) -> MarketInfo:
        return MARKET

    # --- trading -----------------------------------------------------------------------------

    async def create_market_order(self, request: MarketOrderRequest) -> VenueOrder:
        self.create_calls.append(request.client_order_id)
        failure = self._next_failure("create")
        self._raise_before(failure)
        existing = self.orders.get(request.client_order_id)
        if existing is not None:
            return existing.to_venue()
        self._check_funds(request.side, request.quantity, request.symbol)
        order = SimOrder(
            request.client_order_id,
            f"S{len(self.orders) + 1}",
            request.symbol,
            request.side,
            request.quantity,
            "market",
            OrderStatus.OPEN,
        )
        self.orders[order.client_order_id] = order
        self._execute(order, self.price_fn(request.symbol))
        if failure == "timeout_after":
            raise UnknownOutcome("simulated timeout after the exchange accepted the order")
        return order.to_venue()

    async def create_stop_order(self, request: StopOrderRequest) -> VenueOrder:
        failure = self._next_failure("create_stop")
        self._raise_before(failure)
        existing = self.orders.get(request.client_order_id)
        if existing is not None:
            return existing.to_venue()
        self._check_funds(Side.SELL, request.quantity, request.symbol)
        order = SimOrder(
            request.client_order_id,
            f"S{len(self.orders) + 1}",
            request.symbol,
            Side.SELL,
            request.quantity,
            "stop_loss",
            OrderStatus.OPEN,
            stop_price=request.stop_price,
        )
        self.orders[order.client_order_id] = order
        if failure == "timeout_after":
            raise UnknownOutcome("simulated timeout after the exchange accepted the stop")
        return order.to_venue()

    async def fetch_order(self, symbol: str, client_order_id: str) -> VenueOrder | None:
        self.tick()
        order = self.orders.get(client_order_id)
        return order.to_venue() if order else None

    async def cancel_order(self, symbol: str, client_order_id: str) -> VenueOrder:
        self.cancel_calls.append(client_order_id)
        self._raise_before(self._next_failure("cancel"))
        self.tick()
        order = self.orders.get(client_order_id)
        if order is None:
            raise UnknownOrder(client_order_id)
        if order.status is not OrderStatus.OPEN:
            raise ExchangeRejected("Unknown order sent.")  # Binance's answer for a closed order
        order.status = OrderStatus.CANCELED
        return order.to_venue()

    async def fetch_open_orders(self, symbol: str) -> list[VenueOrder]:
        self.tick()
        return [o.to_venue() for o in self.open_orders() if o.symbol == symbol]

    async def fetch_balances(self) -> dict[str, Balance]:
        self.tick()
        locked: dict[str, Decimal] = {}
        for order in self.open_orders():
            if order.side is Side.SELL:
                base = order.symbol.partition("/")[0]
                locked[base] = locked.get(base, Decimal(0)) + order.quantity
        return {
            asset: Balance(
                asset, total - locked.get(asset, Decimal(0)), locked.get(asset, Decimal(0))
            )
            for asset, total in self.balances.items()
            if total
        }

    async def aclose(self) -> None:
        return None

    # --- internals ---------------------------------------------------------------------------

    def _next_failure(self, operation: str) -> str | None:
        queue = self._failures.get(operation)
        return queue.popleft() if queue else None

    @staticmethod
    def _raise_before(failure: str | None) -> None:
        if failure == "reject":
            raise ExchangeRejected("simulated rejection")
        if failure == "timeout_before":
            raise UnknownOutcome("simulated timeout before the request reached the exchange")
        if failure == "auth":
            raise AuthenticationFailed("simulated: API key invalid")
        if failure == "rate_limit":
            raise TransientExchangeError("simulated rate limit")

    def _free(self, asset: str) -> Decimal:
        locked = sum(
            (
                o.quantity
                for o in self.open_orders()
                if o.side is Side.SELL and o.symbol.partition("/")[0] == asset
            ),
            Decimal(0),
        )
        return self.balances.get(asset, Decimal(0)) - locked

    def _check_funds(self, side: Side, quantity: Decimal, symbol: str) -> None:
        base, _, quote = symbol.partition("/")
        if side is Side.BUY:
            if self._free(quote) < quantity * self.price_fn(symbol):
                raise ExchangeRejected("Account has insufficient balance for requested action.")
        elif self._free(base) < quantity:
            raise ExchangeRejected("Account has insufficient balance for requested action.")

    def _execute(self, order: SimOrder, price: Decimal) -> None:
        base, _, quote = order.symbol.partition("/")
        notional = order.quantity * price
        self._trade_seq += 1
        if order.side is Side.BUY:  # Binance: buyers pay the fee in the asset they receive
            fee_base = order.quantity * self.fee_rate
            fill = Fill(
                self.clock.now(),
                Side.BUY,
                order.quantity,
                price,
                Decimal(0),
                fee_base,
                f"T{self._trade_seq}",
            )
            self.balances[quote] = self.balances.get(quote, Decimal(0)) - notional
            self.balances[base] = self.balances.get(base, Decimal(0)) + order.quantity - fee_base
        else:
            fee = notional * self.fee_rate
            fill = Fill(
                self.clock.now(),
                Side.SELL,
                order.quantity,
                price,
                fee,
                Decimal(0),
                f"T{self._trade_seq}",
            )
            self.balances[base] = self.balances.get(base, Decimal(0)) - order.quantity
            self.balances[quote] = self.balances.get(quote, Decimal(0)) + notional - fee
        order.fills.append(fill)
        order.status = OrderStatus.FILLED
