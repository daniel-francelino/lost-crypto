from decimal import Decimal
from typing import Any

import ccxt
import pytest

from factories import T0
from modules.exchanges.errors import ExchangeError, TransientExchangeError, UnknownSymbolError
from modules.exchanges.infrastructure import ccxt_adapter
from modules.exchanges.infrastructure.ccxt_adapter import CcxtMarketDataSource
from modules.market_data.domain.models import Timeframe

BINANCE_MARKET = {
    "info": {
        "filters": [
            {"filterType": "PRICE_FILTER", "tickSize": "0.01000000"},
            {"filterType": "LOT_SIZE", "minQty": "0.00001000", "stepSize": "0.00001000"},
            {"filterType": "NOTIONAL", "minNotional": "5.00000000"},
        ]
    },
}


class FakeClient:
    precisionMode = ccxt.TICK_SIZE

    def __init__(self, market: dict[str, Any] | None = None, failures: int = 0) -> None:
        self.market_data = market or BINANCE_MARKET
        self.failures = failures
        self.calls = 0

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
        return None


@pytest.fixture(autouse=True)
def _no_backoff_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    async def instant(_: float) -> None:
        return None

    monkeypatch.setattr(ccxt_adapter.asyncio, "sleep", instant)


async def test_fetch_candles_converts_to_decimal_candles() -> None:
    source = CcxtMarketDataSource(client=FakeClient())
    (candle,) = await source.fetch_candles("BTC/USDT", Timeframe.H1, T0, 1000)
    assert candle.open_time == T0
    assert str(candle.open) == "100.5" and str(candle.low) == "99.25"
    assert candle.timeframe is Timeframe.H1


async def test_transient_errors_are_retried_then_succeed() -> None:
    client = FakeClient(failures=2)
    source = CcxtMarketDataSource(client=client)
    assert len(await source.fetch_candles("BTC/USDT", Timeframe.H1, T0, 1000)) == 1
    assert client.calls == 3


async def test_gives_up_after_max_attempts() -> None:
    source = CcxtMarketDataSource(client=FakeClient(failures=99))
    with pytest.raises(TransientExchangeError):
        await source.fetch_candles("BTC/USDT", Timeframe.H1, T0, 1000)


async def test_market_info_uses_exact_binance_filters() -> None:
    info = await CcxtMarketDataSource(client=FakeClient()).fetch_market_info("BTC/USDT")
    assert (info.step_size, info.tick_size) == (Decimal("0.00001"), Decimal("0.01"))
    assert (info.min_quantity, info.min_notional) == (Decimal("0.00001"), Decimal(5))


async def test_market_info_falls_back_to_ccxt_precision_and_limits() -> None:
    market = {
        "precision": {"amount": 0.001, "price": 0.01},
        "limits": {"amount": {"min": 0.002}, "cost": {"min": 10}},
    }
    info = await CcxtMarketDataSource(client=FakeClient(market)).fetch_market_info("BTC/USDT")
    assert (info.step_size, info.tick_size, info.min_quantity, info.min_notional) == (
        Decimal("0.001"),
        Decimal("0.01"),
        Decimal("0.002"),
        Decimal(10),
    )


async def test_unknown_symbol_and_missing_precision() -> None:
    source = CcxtMarketDataSource(client=FakeClient())
    with pytest.raises(UnknownSymbolError):
        await source.fetch_market_info("NOPE/USDT")
    with pytest.raises(ExchangeError):
        await CcxtMarketDataSource(client=FakeClient({"info": {}})).fetch_market_info("BTC/USDT")
