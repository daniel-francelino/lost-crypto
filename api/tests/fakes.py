from datetime import datetime
from typing import Any

import ccxt

from factories import T0
from modules.exchanges.application.exchange import Exchange
from modules.exchanges.application.ports import MarketOrderRequest, VenueOrder
from modules.exchanges.application.registry import ExchangeRegistry
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

    async def aclose(self) -> None:
        return None


def fake_registry(source: MarketDataSource) -> ExchangeRegistry:
    """An exchange registry whose 'binance' serves deterministic data instead of the network."""
    registry = ExchangeRegistry()
    registry.register(FakeExchange, lambda: FakeExchange(source))
    return registry
