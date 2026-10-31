from decimal import Decimal

import ccxt
import pytest

from factories import T0
from fakes import FakeCcxtClient
from modules.exchanges.errors import (
    ExchangeError,
    RateLimited,
    TradingNotEnabled,
    TransientExchangeError,
    UnknownSymbolError,
)
from modules.exchanges.infrastructure import ccxt_exchange
from modules.exchanges.infrastructure.binance import BinanceExchange
from modules.market_data.domain.models import MarketInfo, Timeframe


@pytest.fixture(autouse=True)
def _no_backoff_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    async def instant(_: float) -> None:
        return None

    monkeypatch.setattr(ccxt_exchange.asyncio, "sleep", instant)


async def test_fetch_candles_converts_to_decimal_candles() -> None:
    (candle,) = await BinanceExchange(FakeCcxtClient()).fetch_candles(
        "BTC/USDT", Timeframe.H1, T0, 1000
    )
    assert candle.open_time == T0
    assert str(candle.open) == "100.5" and str(candle.low) == "99.25"
    assert candle.timeframe is Timeframe.H1


async def test_transient_errors_are_retried_then_succeed() -> None:
    client = FakeCcxtClient(failures=2)
    assert len(await BinanceExchange(client).fetch_candles("BTC/USDT", Timeframe.H1, T0, 1000)) == 1
    assert client.calls == 3


async def test_gives_up_after_max_attempts() -> None:
    with pytest.raises(TransientExchangeError):
        await BinanceExchange(FakeCcxtClient(failures=99)).fetch_candles(
            "BTC/USDT", Timeframe.H1, T0, 1000
        )


async def test_a_rate_limit_is_never_retried_and_carries_the_retry_after() -> None:
    client = FakeCcxtClient()

    async def limited(*_: object) -> list[list[float]]:
        client.calls += 1
        client.last_response_headers = {"Retry-After": "7"}  # type: ignore[attr-defined]
        raise ccxt.RateLimitExceeded("429")

    client.fetch_ohlcv = limited  # type: ignore[method-assign]
    with pytest.raises(RateLimited) as caught:
        await BinanceExchange(client).fetch_candles("BTC/USDT", Timeframe.H1, T0, 1000)
    assert client.calls == 1
    assert caught.value.retry_after_seconds == 7.0
    assert isinstance(caught.value, TransientExchangeError)


async def test_market_info_uses_exact_binance_filters() -> None:
    info = await BinanceExchange(FakeCcxtClient()).fetch_market_info("BTC/USDT")
    assert info == MarketInfo(
        "BTC/USDT", Decimal("0.00001"), Decimal("0.01"), Decimal("0.00001"), Decimal(5)
    )


async def test_market_info_falls_back_to_ccxt_precision_and_limits() -> None:
    market = {
        "precision": {"amount": 0.001, "price": 0.01},
        "limits": {"amount": {"min": 0.002}, "cost": {"min": 10}},
    }
    info = await BinanceExchange(FakeCcxtClient(market)).fetch_market_info("BTC/USDT")
    assert (info.step_size, info.tick_size, info.min_quantity, info.min_notional) == (
        Decimal("0.001"),
        Decimal("0.01"),
        Decimal("0.002"),
        Decimal(10),
    )


async def test_unknown_symbol_and_missing_precision() -> None:
    with pytest.raises(UnknownSymbolError):
        await BinanceExchange(FakeCcxtClient()).fetch_market_info("NOPE/USDT")
    with pytest.raises(ExchangeError):
        await BinanceExchange(FakeCcxtClient({"info": {}})).fetch_market_info("BTC/USDT")


def test_parse_market_returns_none_without_binance_filters() -> None:
    assert BinanceExchange(FakeCcxtClient()).parse_market("BTC/USDT", {"info": {}}) is None


async def test_real_orders_are_not_enabled_yet() -> None:
    exchange = BinanceExchange(FakeCcxtClient())
    with pytest.raises(TradingNotEnabled):
        await exchange.fetch_order("BTC/USDT", "cid")
    with pytest.raises(TradingNotEnabled):
        await exchange.cancel_order("BTC/USDT", "cid")


async def test_aclose_closes_the_client() -> None:
    client = FakeCcxtClient()
    await BinanceExchange(client).aclose()
    assert client.closed
