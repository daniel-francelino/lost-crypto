"""Exchange registry, Binance profile and the ExchangeGateway contract.

The contract tests are parametrised over gateway factories: a testnet or live adapter must
pass the very same tests to be a drop-in replacement for the paper venue.
"""

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from factories import MARKET
from modules.exchanges.application.ports import ExchangeGateway, MarketOrderRequest
from modules.exchanges.application.registry import ExchangeRegistry
from modules.exchanges.domain.models import (
    ExchangeCapabilities,
    ExchangeProfile,
    FeeSchedule,
    InvalidFeeSchedule,
    OrderType,
)
from modules.exchanges.errors import (
    ExchangeRejected,
    UnknownExchangeError,
    UnknownOrder,
    UnsupportedTimeframeError,
)
from modules.exchanges.infrastructure.binance import BINANCE_PROFILE, binance_market_info
from modules.exchanges.infrastructure.catalog import build_exchange_registry
from modules.execution.domain.orders import OrderStatus
from modules.execution.venues.paper import PaperExchangeGateway, StaticPriceFeed
from modules.market_data.domain.models import MarketInfo, Timeframe
from modules.strategies.domain.types import Side

NOW = datetime(2024, 1, 1, tzinfo=UTC)


class _Rules:
    async def fetch_market_info(self, symbol: str) -> MarketInfo:
        return MARKET


class _Source:
    closed = False

    async def aclose(self) -> None:
        self.closed = True


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


# --- registry -----------------------------------------------------------------------------


def test_registry_resolves_profiles_and_rejects_unknown_exchanges() -> None:
    registry = ExchangeRegistry()
    registry.register(_profile("kraken"), lambda: _Source())  # type: ignore[arg-type,return-value]
    registry.register(BINANCE_PROFILE, lambda: _Source())  # type: ignore[arg-type,return-value]
    assert registry.exchange_ids() == ["binance", "kraken"]
    assert registry.profile("kraken").fees.taker_rate == Decimal("0.003")
    with pytest.raises(UnknownExchangeError, match="available: binance, kraken"):
        registry.profile("ftx")


def test_registry_checks_timeframe_support() -> None:
    registry = ExchangeRegistry()
    registry.register(_profile("hourly", frozenset({Timeframe.H1})), lambda: _Source())  # type: ignore[arg-type,return-value]
    assert registry.require("hourly", Timeframe.H1).exchange_id == "hourly"
    with pytest.raises(UnsupportedTimeframeError):
        registry.require("hourly", Timeframe.M1)


async def test_registry_creates_market_data_lazily_once_and_closes_it() -> None:
    created: list[_Source] = []

    def factory() -> _Source:
        created.append(_Source())
        return created[-1]

    registry = ExchangeRegistry()
    registry.register(_profile("x"), factory)  # type: ignore[arg-type]
    assert created == []
    first = registry.market_data("x")
    assert registry.market_data("x") is first and len(created) == 1
    await registry.aclose()
    assert created[0].closed


def test_default_catalog_offers_binance_with_its_facts() -> None:
    registry = build_exchange_registry()
    profile = registry.profile("binance")
    caps = profile.capabilities
    assert registry.exchange_ids() == ["binance"]
    assert caps.native_stop_orders and caps.has_testnet
    assert caps.max_client_order_id_length == 36
    assert OrderType.MARKET in caps.order_types
    assert set(Timeframe) <= caps.timeframes


def test_fee_schedule_validates_rates() -> None:
    with pytest.raises(InvalidFeeSchedule):
        FeeSchedule(Decimal("-0.1"), Decimal("0.001"))
    with pytest.raises(InvalidFeeSchedule):
        FeeSchedule(Decimal("0.001"), Decimal(1))


def test_binance_parser_reads_exchange_filters_and_defers_otherwise() -> None:
    market = {
        "info": {
            "filters": [
                {"filterType": "PRICE_FILTER", "tickSize": "0.01"},
                {"filterType": "LOT_SIZE", "minQty": "0.001", "stepSize": "0.001"},
                {"filterType": "NOTIONAL", "minNotional": "5"},
            ]
        }
    }
    info = binance_market_info("BTC/USDT", market)
    assert info == MarketInfo(
        "BTC/USDT", Decimal("0.001"), Decimal("0.01"), Decimal("0.001"), Decimal(5)
    )
    assert binance_market_info("BTC/USDT", {"info": {}}) is None


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


async def test_contract_market_order_fills_with_slippage_and_fee(gateway: ExchangeGateway) -> None:
    order = await gateway.create_market_order(_request(quantity="1.5"))
    assert order.status is OrderStatus.FILLED
    assert order.filled_quantity == Decimal("1.5") == sum(f.quantity for f in order.fills)
    (fill,) = order.fills
    assert fill.price == Decimal("100.1")  # 10 bps adverse slippage on a buy
    assert fill.fee == fill.notional * Decimal("0.001")


async def test_contract_sell_slips_the_other_way(gateway: ExchangeGateway) -> None:
    order = await gateway.create_market_order(_request(side=Side.SELL))
    assert order.fills[0].price == Decimal("99.9")


async def test_contract_create_is_idempotent_on_client_order_id(gateway: ExchangeGateway) -> None:
    first = await gateway.create_market_order(_request("same-id"))
    again = await gateway.create_market_order(_request("same-id"))
    assert again == first  # same order back, no second fill


async def test_contract_quantity_is_validated_against_market_rules(
    gateway: ExchangeGateway,
) -> None:
    with pytest.raises(ExchangeRejected):
        await gateway.create_market_order(_request("tiny", quantity="0.0001"))  # < min quantity


async def test_contract_rejects_oversized_client_order_ids(gateway: ExchangeGateway) -> None:
    limit = gateway.capabilities.max_client_order_id_length
    with pytest.raises(ExchangeRejected):
        await gateway.create_market_order(_request("x" * (limit + 1)))


async def test_contract_fetch_and_cancel(gateway: ExchangeGateway) -> None:
    assert await gateway.fetch_order("BTC/USDT", "nope") is None
    with pytest.raises(UnknownOrder):
        await gateway.cancel_order("BTC/USDT", "nope")
    placed = await gateway.create_market_order(_request("known"))
    assert await gateway.fetch_order("BTC/USDT", "known") == placed
    with pytest.raises(ExchangeRejected):  # market orders fill at once: nothing left to cancel
        await gateway.cancel_order("BTC/USDT", "known")


async def test_contract_exposes_capabilities(gateway: ExchangeGateway) -> None:
    assert gateway.capabilities.exchange_id == "binance"
