"""Exchange contract, registry, catalog and the ExchangeGateway contract.

The contract tests are parametrised over implementations: a new exchange file (or a testnet /
live gateway) must pass the very same tests to be a drop-in replacement.
"""

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from core.config import Settings
from factories import MARKET, T0
from fakes import FakeCcxtClient
from modules.exchanges.application.exchange import Exchange
from modules.exchanges.application.ports import (
    Balance,
    ExchangeGateway,
    MarketOrderRequest,
    StopOrderRequest,
    VenueOrder,
)
from modules.exchanges.application.registry import ExchangeRegistry
from modules.exchanges.domain.connections import ApiPermissions
from modules.exchanges.domain.models import (
    ExchangeCapabilities,
    ExchangeProfile,
    FeeSchedule,
    InvalidFeeSchedule,
    OrderType,
)
from modules.exchanges.errors import (
    ExchangeConfigurationError,
    ExchangeRejected,
    TradingNotEnabled,
    UnknownExchangeError,
    UnknownOrder,
    UnknownSymbolError,
    UnsupportedTimeframeError,
)
from modules.exchanges.infrastructure.binance import BINANCE_PROFILE, BinanceExchange
from modules.exchanges.infrastructure.catalog import AVAILABLE_EXCHANGES, build_exchange_registry
from modules.execution.domain.orders import OrderStatus
from modules.execution.venues.paper import PaperExchangeGateway, StaticPriceFeed
from modules.market_data.domain.models import Candle, MarketInfo, Timeframe
from modules.strategies.domain.types import Side

NOW = datetime(2024, 1, 1, tzinfo=UTC)


class _Rules:
    async def fetch_market_info(self, symbol: str) -> MarketInfo:
        return MARKET


def _profile(exchange_id: str, timeframes: frozenset[Timeframe] | None = None) -> ExchangeProfile:
    return ExchangeProfile(
        ExchangeCapabilities(
            exchange_id=exchange_id,
            name=exchange_id.title(),
            order_types=frozenset({OrderType.MARKET}),
            native_stop_orders=False,
            max_client_order_id_length=36,
            has_testnet=False,
            timeframes=timeframes or frozenset(Timeframe),
        ),
        FeeSchedule(Decimal("0.002"), Decimal("0.003")),
    )


def _exchange_class(
    exchange_id: str, timeframes: frozenset[Timeframe] | None = None
) -> type[Exchange]:
    """A minimal but complete exchange integration (what a new exchange file looks like)."""
    closed: list[bool] = []

    class _Example(Exchange):
        PROFILE = _profile(exchange_id, timeframes)
        was_closed = closed

        async def fetch_candles(
            self, symbol: str, timeframe: Timeframe, since: datetime, limit: int
        ) -> list[Candle]:
            return []

        async def fetch_market_info(self, symbol: str) -> MarketInfo:
            return MARKET

        async def create_market_order(self, request: MarketOrderRequest) -> VenueOrder:
            raise TradingNotEnabled(exchange_id)

        async def fetch_order(self, symbol: str, client_order_id: str) -> VenueOrder | None:
            return None

        async def cancel_order(self, symbol: str, client_order_id: str) -> VenueOrder:
            raise TradingNotEnabled(exchange_id)

        async def create_stop_order(self, request: StopOrderRequest) -> VenueOrder:
            raise TradingNotEnabled(exchange_id)

        async def fetch_open_orders(self, symbol: str) -> list[VenueOrder]:
            return []

        async def fetch_balances(self) -> dict[str, Balance]:
            return {}

        async def fetch_api_permissions(self) -> ApiPermissions:
            raise TradingNotEnabled(exchange_id)

        async def aclose(self) -> None:
            closed.append(True)

    return _Example


# --- the Exchange contract itself -----------------------------------------------------------


def test_an_exchange_that_leaves_methods_unimplemented_cannot_be_instantiated() -> None:
    class Incomplete(Exchange):
        PROFILE = _profile("incomplete")

        async def fetch_candles(self, *args: Any, **kwargs: Any) -> list[Candle]:
            return []

    with pytest.raises(TypeError, match="abstract"):
        Incomplete()  # type: ignore[abstract]


def test_registering_a_class_without_a_profile_is_refused() -> None:
    # The abstract contract itself declares PROFILE but does not provide one: a subclass that
    # forgets to set it must be refused at registration, not fail later at runtime.
    with pytest.raises(ExchangeConfigurationError, match="PROFILE"):
        ExchangeRegistry().register(Exchange)


EXCHANGE_FACTORIES: list[Callable[[], Exchange]] = [lambda: BinanceExchange(FakeCcxtClient())]


@pytest.fixture(params=EXCHANGE_FACTORIES, ids=["binance"])
def exchange(request: pytest.FixtureRequest) -> Exchange:
    return request.param()  # type: ignore[no-any-return]


async def test_contract_fetch_candles_returns_decimal_candles(exchange: Exchange) -> None:
    candles = await exchange.fetch_candles("BTC/USDT", Timeframe.H1, T0, 100)
    assert candles and all(isinstance(c, Candle) for c in candles)
    assert all(isinstance(c.close, Decimal) and c.open_time.tzinfo for c in candles)
    assert [c.open_time for c in candles] == sorted(c.open_time for c in candles)


async def test_contract_fetch_market_info_returns_usable_rules(exchange: Exchange) -> None:
    info = await exchange.fetch_market_info("BTC/USDT")
    assert info.step_size > 0 and info.tick_size > 0 and info.min_notional >= 0


async def test_contract_unknown_symbols_raise_unknown_symbol(exchange: Exchange) -> None:
    with pytest.raises(UnknownSymbolError):
        await exchange.fetch_market_info("NOPE/USDT")


async def test_contract_declares_a_complete_profile(exchange: Exchange) -> None:
    caps = exchange.capabilities
    assert caps is exchange.PROFILE.capabilities and caps.exchange_id and caps.timeframes
    assert OrderType.MARKET in caps.order_types
    assert exchange.PROFILE.fees.taker_rate >= 0


async def test_contract_trading_is_gated_until_it_is_enabled(exchange: Exchange) -> None:
    request = MarketOrderRequest("cid", "BTC/USDT", Side.BUY, Decimal(1))
    with pytest.raises(TradingNotEnabled):
        await exchange.create_market_order(request)


async def test_contract_aclose_is_safe(exchange: Exchange) -> None:
    await exchange.aclose()


# --- registry and catalog -------------------------------------------------------------------


def test_registry_resolves_profiles_and_rejects_unknown_exchanges() -> None:
    registry = ExchangeRegistry()
    registry.register(_exchange_class("kraken"))
    registry.register(BinanceExchange)
    assert registry.exchange_ids() == ["binance", "kraken"]
    assert registry.profile("kraken").fees.taker_rate == Decimal("0.003")
    with pytest.raises(UnknownExchangeError, match=r"enabled: binance, kraken"):
        registry.profile("ftx")


def test_registry_checks_timeframe_support() -> None:
    registry = ExchangeRegistry()
    registry.register(_exchange_class("hourly", frozenset({Timeframe.H1})))
    assert registry.require("hourly", Timeframe.H1).exchange_id == "hourly"
    with pytest.raises(UnsupportedTimeframeError):
        registry.require("hourly", Timeframe.M1)


async def test_registry_creates_the_integration_lazily_once_and_closes_it() -> None:
    cls = _exchange_class("x")
    created: list[Exchange] = []

    def factory() -> Exchange:
        created.append(cls())
        return created[-1]

    registry = ExchangeRegistry()
    registry.register(cls, factory)
    registry.profile("x")  # reading the profile must not build a client
    assert created == []
    first = registry.exchange("x")
    assert registry.market_data("x") is first and len(created) == 1
    await registry.aclose()
    assert cls.was_closed == [True]  # type: ignore[attr-defined]


def test_default_catalog_offers_binance_with_its_facts() -> None:
    registry = build_exchange_registry()
    caps = registry.profile("binance").capabilities
    assert registry.exchange_ids() == ["binance"]
    assert caps.native_stop_orders and caps.has_testnet
    assert caps.max_client_order_id_length == 36
    assert set(Timeframe) <= caps.timeframes


def test_catalog_enables_only_what_the_deployment_selects() -> None:
    assert set(AVAILABLE_EXCHANGES) == {"binance"}
    with pytest.raises(ExchangeConfigurationError, match="no integration"):
        build_exchange_registry(["ftx"])
    with pytest.raises(ExchangeConfigurationError, match="at least one"):
        build_exchange_registry([])


def test_enabled_exchanges_setting_is_parsed_from_a_comma_separated_list() -> None:
    settings = Settings(_env_file=None, enabled_exchanges=" binance , kraken ,")  # type: ignore[call-arg]
    assert settings.enabled_exchange_ids == ["binance", "kraken"]
    assert Settings(_env_file=None).enabled_exchange_ids == ["binance"]  # type: ignore[call-arg]


def test_fee_schedule_validates_rates() -> None:
    with pytest.raises(InvalidFeeSchedule):
        FeeSchedule(Decimal("-0.1"), Decimal("0.001"))
    with pytest.raises(InvalidFeeSchedule):
        FeeSchedule(Decimal("0.001"), Decimal(1))


# --- gateway contract ---------------------------------------------------------------------


def _paper(price: str = "100") -> ExchangeGateway:
    feed = StaticPriceFeed()
    feed.set("BTC/USDT", Decimal(price), NOW)
    return PaperExchangeGateway(
        BINANCE_PROFILE.capabilities, _Rules(), feed, Decimal("0.001"), Decimal(10)
    )


GATEWAY_FACTORIES: list[Callable[[], ExchangeGateway]] = [_paper]


def _request(client_id: str = "cid-1", quantity: str = "1", side: Side = Side.BUY):  # type: ignore[no-untyped-def]
    return MarketOrderRequest(client_id, "BTC/USDT", side, Decimal(quantity))


@pytest.fixture(params=GATEWAY_FACTORIES, ids=lambda f: f.__name__)
def gateway(request: pytest.FixtureRequest) -> ExchangeGateway:
    return request.param()  # type: ignore[no-any-return]


async def test_gateway_contract_market_order_fills_with_slippage_and_fee(
    gateway: ExchangeGateway,
) -> None:
    order = await gateway.create_market_order(_request(quantity="1.5"))
    assert order.status is OrderStatus.FILLED
    assert order.filled_quantity == Decimal("1.5") == sum(f.quantity for f in order.fills)
    (fill,) = order.fills
    assert fill.price == Decimal("100.1")  # 10 bps adverse slippage on a buy
    assert fill.fee == fill.notional * Decimal("0.001")


async def test_gateway_contract_sell_slips_the_other_way(gateway: ExchangeGateway) -> None:
    order = await gateway.create_market_order(_request(side=Side.SELL))
    assert order.fills[0].price == Decimal("99.9")


async def test_gateway_contract_create_is_idempotent_on_client_order_id(
    gateway: ExchangeGateway,
) -> None:
    first = await gateway.create_market_order(_request("same-id"))
    again = await gateway.create_market_order(_request("same-id"))
    assert again == first  # same order back, no second fill


async def test_gateway_contract_quantity_is_validated_against_market_rules(
    gateway: ExchangeGateway,
) -> None:
    with pytest.raises(ExchangeRejected):
        await gateway.create_market_order(_request("tiny", quantity="0.0001"))  # < min quantity


async def test_gateway_contract_rejects_oversized_client_order_ids(
    gateway: ExchangeGateway,
) -> None:
    limit = gateway.capabilities.max_client_order_id_length
    with pytest.raises(ExchangeRejected):
        await gateway.create_market_order(_request("x" * (limit + 1)))


async def test_gateway_contract_fetch_and_cancel(gateway: ExchangeGateway) -> None:
    assert await gateway.fetch_order("BTC/USDT", "nope") is None
    with pytest.raises(UnknownOrder):
        await gateway.cancel_order("BTC/USDT", "nope")
    placed = await gateway.create_market_order(_request("known"))
    assert await gateway.fetch_order("BTC/USDT", "known") == placed
    with pytest.raises(ExchangeRejected):  # market orders fill at once: nothing left to cancel
        await gateway.cancel_order("BTC/USDT", "known")


async def test_gateway_contract_exposes_capabilities(gateway: ExchangeGateway) -> None:
    assert gateway.capabilities.exchange_id == "binance"
