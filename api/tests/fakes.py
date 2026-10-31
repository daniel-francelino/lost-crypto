from datetime import datetime
from typing import Any

import ccxt

from factories import T0
from modules.exchanges.application.exchange import Exchange
from modules.exchanges.application.ports import (
    Balance,
    MarketOrderRequest,
    StopOrderRequest,
    VenueOrder,
)
from modules.exchanges.application.registry import ExchangeRegistry
from modules.exchanges.domain.connections import ApiPermissions
from modules.exchanges.errors import TradingNotEnabled
from modules.exchanges.infrastructure.binance import BINANCE_PROFILE
from modules.market_data.application.ports import MarketDataSource
from modules.market_data.domain.models import Candle, MarketInfo, Timeframe

BINANCE_RAW_MARKET = {
    "info": {
        "filters": [
            {"filterType": "PRICE_FILTER", "tickSize": "0.01000000"},
            {"filterType": "LOT_SIZE", "minQty": "0.00001000", "stepSize": "0.00001000"},
            {"filterType": "NOTIONAL", "minNotional": "5.00000000"},
        ]
    },
}


class FakeCcxtClient:
    """Stands in for a ccxt.async_support exchange object."""

    precisionMode = ccxt.TICK_SIZE

    def __init__(self, market: dict[str, Any] | None = None, failures: int = 0) -> None:
        self.market_data = market or BINANCE_RAW_MARKET
        self.failures = failures
        self.calls = 0
        self.closed = False

    async def load_markets(self) -> None:
        return None

    def market(self, symbol: str) -> dict[str, Any]:
        if symbol == "NOPE/USDT":
            raise ccxt.BadSymbol("nope")
        return self.market_data

    async def fetch_ohlcv(self, symbol: str, tf: str, since: int, limit: int) -> list[list[float]]:
        self.calls += 1
        if self.calls <= self.failures:
            raise ccxt.NetworkError("boom")
        return [[int(T0.timestamp() * 1000), 100.5, 101, 99.25, 100, 12.5]]

    async def close(self) -> None:
        self.closed = True

    # --- order endpoints: tests script responses/errors through these attributes ---------------
    order_response: dict[str, Any] | None = None
    order_error: Exception | None = None
    lookup_response: dict[str, Any] | None = None
    lookup_error: Exception | None = None
    my_trades: list[dict[str, Any]] | None = None
    open_orders_response: list[dict[str, Any]] | None = None
    balance_response: dict[str, Any] | None = None
    last_create: tuple[Any, ...] | None = None
    last_lookup: tuple[Any, ...] | None = None

    async def create_order(self, *args: Any) -> dict[str, Any]:
        self.last_create = args
        if self.order_error is not None:
            raise self.order_error
        assert self.order_response is not None
        return self.order_response

    async def fetch_order(self, *args: Any) -> dict[str, Any]:
        self.last_lookup = args
        if self.lookup_error is not None:
            raise self.lookup_error
        assert self.lookup_response is not None
        return self.lookup_response

    async def cancel_order(self, *args: Any) -> dict[str, Any]:
        self.last_lookup = args
        if self.lookup_error is not None:
            raise self.lookup_error
        return self.lookup_response or {"status": "canceled", "side": "sell", "amount": 1}

    async def fetch_my_trades(self, *args: Any) -> list[dict[str, Any]]:
        return self.my_trades or []

    async def fetch_open_orders(self, symbol: str) -> list[dict[str, Any]]:
        return self.open_orders_response or []

    async def fetch_balance(self) -> dict[str, Any]:
        return self.balance_response or {"total": {}, "free": {}, "used": {}}


class FakeExchange(Exchange):
    """A fully working integration serving data from any ``MarketDataSource`` (for tests)."""

    PROFILE = BINANCE_PROFILE

    def __init__(self, source: MarketDataSource) -> None:
        self._source = source

    async def fetch_candles(
        self, symbol: str, timeframe: Timeframe, since: datetime, limit: int
    ) -> list[Candle]:
        return await self._source.fetch_candles(symbol, timeframe, since, limit)

    async def fetch_market_info(self, symbol: str) -> MarketInfo:
        return await self._source.fetch_market_info(symbol)

    async def create_market_order(self, request: MarketOrderRequest) -> VenueOrder:
        raise TradingNotEnabled("fake exchange")

    async def fetch_order(self, symbol: str, client_order_id: str) -> VenueOrder | None:
        raise TradingNotEnabled("fake exchange")

    async def cancel_order(self, symbol: str, client_order_id: str) -> VenueOrder:
        raise TradingNotEnabled("fake exchange")

    async def create_stop_order(self, request: StopOrderRequest) -> VenueOrder:
        raise TradingNotEnabled("fake exchange")

    async def fetch_open_orders(self, symbol: str) -> list[VenueOrder]:
        raise TradingNotEnabled("fake exchange")

    async def fetch_balances(self) -> dict[str, Balance]:
        raise TradingNotEnabled("fake exchange")

    async def fetch_api_permissions(self) -> ApiPermissions:
        raise TradingNotEnabled("fake exchange")

    async def aclose(self) -> None:
        return None


def fake_registry(source: MarketDataSource) -> ExchangeRegistry:
    """An exchange registry whose 'binance' serves deterministic data instead of the network."""
    registry = ExchangeRegistry()
    registry.register(FakeExchange, lambda: FakeExchange(source))
    return registry


def sim_registry(exchange: Exchange) -> ExchangeRegistry:
    """A registry whose 'binance' (public and authenticated) is one simulated account."""
    registry = ExchangeRegistry()
    registry.register(
        type(exchange), lambda: exchange, authenticated=lambda credentials, environment: exchange
    )
    return registry
