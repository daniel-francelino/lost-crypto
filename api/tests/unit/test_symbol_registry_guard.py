"""Only registered pairs may be used by bots, backtests and candle imports."""

from datetime import timedelta
from typing import Any, cast
from uuid import uuid4

import pytest
from test_bot_config_update import _config

from core.errors import DomainError
from core.ids import UuidGenerator
from core.symbols import AllowAnySymbol, SymbolNotRegistered
from factories import T0, make_config
from fakes import fake_registry
from modules.backtesting.application.service import BacktestService
from modules.bots.application.service import BotService
from modules.exchanges.domain.models import TradingProduct
from modules.market_data.application.service import MarketDataService
from modules.market_data.domain.models import Timeframe
from modules.strategies.catalog import build_strategy_registry
from modules.trends.application.guard import RegistrySymbolGuard
from modules.trends.domain.models import WatchedSymbol

EXCHANGE = "binance"


class _Trends:
    def __init__(self, *symbols: WatchedSymbol) -> None:
        self.symbols = list(symbols)

    async def find_symbol(self, exchange: str, symbol: str) -> WatchedSymbol | None:
        return next((s for s in self.symbols if (s.exchange, s.symbol) == (exchange, symbol)), None)

    async def list_symbols(self, *, active_only: bool) -> list[WatchedSymbol]:
        return [s for s in self.symbols if s.active or not active_only]


class _Store:
    def __init__(self, *symbols: WatchedSymbol) -> None:
        self.trends = _Trends(*symbols)


def _guard(*symbols: WatchedSymbol) -> RegistrySymbolGuard:
    store = _Store(*symbols)

    class _Scope:
        async def __aenter__(self) -> _Store:
            return store

        async def __aexit__(self, *args: Any) -> None:
            return None

    return RegistrySymbolGuard(lambda: cast(Any, _Scope()))


def _watched(symbol: str, active: bool = True) -> WatchedSymbol:
    return WatchedSymbol(uuid4(), EXCHANGE, symbol, active, T0)


async def test_a_registered_active_pair_passes() -> None:
    await _guard(_watched("BTC/USDT")).require(EXCHANGE, "BTC/USDT")


@pytest.mark.parametrize(
    ("registered", "asked"),
    [
        (None, "BTC/USDT"),  # nothing registered
        (_watched("ETH/USDT"), "BTC/USDT"),  # another pair
        (_watched("BTC/USDT", active=False), "BTC/USDT"),  # switched off
    ],
)
async def test_anything_else_is_refused_with_a_hint(
    registered: WatchedSymbol | None, asked: str
) -> None:
    guard = _guard() if registered is None else _guard(registered)
    with pytest.raises(SymbolNotRegistered, match="register it"):
        await guard.require(EXCHANGE, asked)
    assert issubclass(SymbolNotRegistered, DomainError)  # the API answers 422


async def test_the_pair_is_scoped_to_its_exchange() -> None:
    with pytest.raises(SymbolNotRegistered):
        await _guard(_watched("BTC/USDT")).require("binance-usdm", "BTC/USDT")


async def test_active_pairs_lists_only_the_active_ones() -> None:
    guard = _guard(_watched("BTC/USDT"), _watched("ETH/USDT", active=False))
    assert await guard.active_pairs() == {(EXCHANGE, "BTC/USDT")}


async def test_without_a_registry_in_force_everything_passes() -> None:
    await AllowAnySymbol().require(EXCHANGE, "WHATEVER/USDT")


# --- the entry points of the rest of the system -------------------------------------------------


async def test_a_bot_cannot_be_created_on_an_unregistered_pair() -> None:
    service = BotService(
        cast(Any, None),
        build_strategy_registry(),
        fake_registry(cast(Any, None)),
        cast(Any, None),
        UuidGenerator(),
        cast(Any, None),
        _guard(),
    )
    with pytest.raises(SymbolNotRegistered):
        await service.create(_config(TradingProduct.SPOT))


async def test_a_backtest_and_a_sweep_cannot_use_an_unregistered_pair() -> None:
    service = BacktestService(
        cast(Any, None),
        build_strategy_registry(),
        fake_registry(cast(Any, None)),
        cast(Any, None),
        UuidGenerator(),
        None,
        _guard(),
    )
    config = make_config()
    with pytest.raises(SymbolNotRegistered):
        await service.create(config)
    with pytest.raises(SymbolNotRegistered):
        await service.create_sweep(config, {"fast_period": [2, 3]})


async def test_a_candle_import_cannot_use_an_unregistered_pair() -> None:
    service = MarketDataService(
        cast(Any, None),
        fake_registry(cast(Any, None)),
        cast(Any, None),
        UuidGenerator(),
        _guard(),
    )
    with pytest.raises(SymbolNotRegistered):
        await service.request_import(
            EXCHANGE, "BTC/USDT", Timeframe.H1, T0, T0 + timedelta(hours=5)
        )
