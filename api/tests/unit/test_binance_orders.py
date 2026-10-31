"""Real-order handling of the CCXT-based exchange, driven by Binance-shaped payloads.

The payloads mirror Binance's documented spot responses (``fills`` with ``commission`` /
``commissionAsset`` / ``tradeId``) wrapped the way CCXT unifies them. They are NOT a recording of
the live testnet: ``tests/testnet_smoke.py`` is the opt-in check against the real thing.
"""

from decimal import Decimal
from typing import Any

import ccxt
import pytest

from fakes import FakeCcxtClient
from modules.exchanges.application.ports import MarketOrderRequest, StopOrderRequest
from modules.exchanges.domain.connections import Credentials
from modules.exchanges.errors import (
    AuthenticationFailed,
    ExchangeRejected,
    NotAuthenticated,
    TradingNotEnabled,
    TransientExchangeError,
    UnknownOrder,
    UnknownOutcome,
    UnsupportedFeeAsset,
)
from modules.exchanges.infrastructure.binance import BinanceExchange
from modules.exchanges.infrastructure.ccxt_orders import parse_balances, parse_order
from modules.execution.domain.orders import OrderStatus
from modules.strategies.domain.types import Side

CREDENTIALS = Credentials("test-api-key-1234", "test-api-secret-5678")
CID = "lc-0123456789abcdef0123456789abcdef"
SYMBOL = "BTC/USDT"
BUY = MarketOrderRequest(CID, SYMBOL, Side.BUY, Decimal("0.5"))


def _buy_response(fee_asset: str = "BTC", commission: str = "0.0005") -> dict[str, Any]:
    """CCXT's unified order for a filled Binance market buy of 0.5 BTC at 60000."""
    return {
        "id": "28",
        "clientOrderId": CID,
        "symbol": SYMBOL,
        "side": "buy",
        "type": "market",
        "status": "closed",
        "amount": 0.5,
        "filled": 0.5,
        "timestamp": 1_700_000_000_000,
        "trades": [],
        "info": {
            "orderId": 28,
            "clientOrderId": CID,
            "status": "FILLED",
            "fills": [
                {
                    "price": "60000.00000000",
                    "qty": "0.30000000",
                    "commission": commission if fee_asset == "BTC" else "9.00",
                    "commissionAsset": fee_asset,
                    "tradeId": 56,
                },
                {
                    "price": "60010.00000000",
                    "qty": "0.20000000",
                    "commission": "0.0002" if fee_asset == "BTC" else "6.00",
                    "commissionAsset": fee_asset,
                    "tradeId": 57,
                },
            ],
        },
    }


def _authenticated(client: FakeCcxtClient | None = None) -> tuple[BinanceExchange, FakeCcxtClient]:
    client = client or FakeCcxtClient()
    return BinanceExchange(client, credentials=CREDENTIALS), client


# --- parsing --------------------------------------------------------------------------------


async def test_market_buy_is_parsed_with_base_asset_fees_and_trade_ids() -> None:
    exchange, client = _authenticated()
    client.order_response = _buy_response()
    order = await exchange.create_market_order(BUY)

    assert (order.status, order.filled_quantity, order.exchange_order_id) == (
        OrderStatus.FILLED,
        Decimal("0.5"),
        "28",
    )
    first, second = order.fills
    assert (first.trade_id, first.quantity, first.price) == ("56", Decimal("0.3"), Decimal(60000))
    assert (first.fee, first.fee_base) == (Decimal(0), Decimal("0.0005"))  # fee paid in BTC
    assert second.fee_base == Decimal("0.0002")
    # The value of a base-asset fee is part of the position's cost.
    assert first.total_fee == Decimal("0.0005") * Decimal(60000)
    # What we sent: our client id, market type, the quantity.
    assert client.last_create == (SYMBOL, "market", "buy", 0.5, None, {"newClientOrderId": CID})


async def test_sell_fee_in_quote_asset_is_kept_in_quote() -> None:
    exchange, client = _authenticated()
    response = _buy_response(fee_asset="USDT")
    response["side"] = "sell"
    client.order_response = response
    order = await exchange.create_market_order(
        MarketOrderRequest(CID, SYMBOL, Side.SELL, Decimal("0.5"))
    )
    assert order.fills[0].fee == Decimal("9.00") and order.fills[0].fee_base == 0


async def test_fees_in_an_unvalueable_asset_are_refused_loudly() -> None:
    exchange, client = _authenticated()
    client.order_response = _buy_response(fee_asset="BNB")
    with pytest.raises(UnsupportedFeeAsset, match="BNB"):
        await exchange.create_market_order(BUY)


@pytest.mark.parametrize(
    ("raw_status", "filled", "expected"),
    [
        ("open", 0, OrderStatus.OPEN),
        ("open", 0.2, OrderStatus.PARTIALLY_FILLED),
        ("closed", 0.5, OrderStatus.FILLED),
        ("canceled", 0, OrderStatus.CANCELED),
        ("expired", 0, OrderStatus.EXPIRED),
        ("rejected", 0, OrderStatus.REJECTED),
    ],
)
def test_order_status_mapping(raw_status: str, filled: float, expected: OrderStatus) -> None:
    raw = {
        "id": "1",
        "clientOrderId": CID,
        "side": "buy",
        "status": raw_status,
        "amount": 0.5,
        "filled": filled,
        "trades": [],
    }
    assert parse_order(raw, SYMBOL, trades=[]).status is expected


def test_unknown_status_is_an_error_not_a_guess() -> None:
    with pytest.raises(Exception, match="unexpected order status"):
        parse_order({"side": "buy", "status": "weird", "amount": 1, "filled": 0}, SYMBOL, trades=[])


def test_stop_orders_expose_their_trigger() -> None:
    raw = {
        "id": "9",
        "clientOrderId": "x-sl",
        "side": "sell",
        "type": "stop_loss",
        "status": "open",
        "amount": 0.5,
        "filled": 0,
        "stopPrice": 59000.0,
    }
    order = parse_order(raw, SYMBOL, trades=[])
    assert (order.order_type, order.stop_price, order.status) == (
        "stop_loss",
        Decimal(59000),
        OrderStatus.OPEN,
    )


def test_balances_keep_only_assets_with_funds() -> None:
    raw = {
        "total": {"USDT": 1000, "BTC": 0.5, "ETH": 0},
        "free": {"USDT": 900, "BTC": 0.5, "ETH": 0},
        "used": {"USDT": 100, "BTC": 0, "ETH": 0},
    }
    balances = parse_balances(raw)
    assert set(balances) == {"USDT", "BTC"}
    assert (balances["USDT"].free, balances["USDT"].locked, balances["USDT"].total) == (
        Decimal(900),
        Decimal(100),
        Decimal(1000),
    )


# --- looking orders up ----------------------------------------------------------------------


async def test_fetch_order_by_client_id_and_executions_from_my_trades() -> None:
    exchange, client = _authenticated()
    response = _buy_response()
    response["info"] = {}  # a lookup does not carry the fills: they come from my trades
    client.lookup_response = response
    client.my_trades = [
        {
            "id": "56",
            "price": "60000",
            "amount": "0.5",
            "timestamp": 1_700_000_000_000,
            "fee": {"cost": "0.0005", "currency": "BTC"},
        }
    ]
    order = await exchange.fetch_order(SYMBOL, CID)
    assert order is not None and order.fills[0].trade_id == "56"
    assert client.last_lookup == (CID, SYMBOL, {"origClientOrderId": CID})


async def test_fetch_order_returns_none_when_the_exchange_does_not_know_it() -> None:
    exchange, client = _authenticated()
    client.lookup_error = ccxt.OrderNotFound("binance Order does not exist")
    assert await exchange.fetch_order(SYMBOL, CID) is None


async def test_cancel_of_an_unknown_order_raises_unknown_order() -> None:
    exchange, client = _authenticated()
    client.lookup_error = ccxt.OrderNotFound("Unknown order sent")
    with pytest.raises(UnknownOrder):
        await exchange.cancel_order(SYMBOL, CID)


async def test_stop_order_request_carries_the_trigger_and_client_id() -> None:
    exchange, client = _authenticated()
    client.order_response = {
        "id": "9",
        "clientOrderId": "x-sl",
        "side": "sell",
        "type": "stop_loss",
        "status": "open",
        "amount": 0.5,
        "filled": 0,
        "stopPrice": 59000.0,
    }
    order = await exchange.create_stop_order(
        StopOrderRequest("x-sl", SYMBOL, Decimal("0.5"), Decimal(59000))
    )
    assert order.status is OrderStatus.OPEN
    assert client.last_create == (
        SYMBOL,
        "STOP_LOSS",
        "sell",
        0.5,
        None,
        {"newClientOrderId": "x-sl", "stopPrice": 59000.0},
    )


# --- failure semantics: the heart of "never duplicate an order" -------------------------------


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (ccxt.NetworkError("connection reset"), UnknownOutcome),  # may have reached the exchange
        (ccxt.RequestTimeout("timed out"), UnknownOutcome),
        (ccxt.ExchangeNotAvailable("502"), UnknownOutcome),
        (ccxt.ExchangeError("something odd"), UnknownOutcome),
        (ccxt.RateLimitExceeded("429"), TransientExchangeError),  # provably not processed
        (ccxt.InsufficientFunds("balance"), ExchangeRejected),
        (ccxt.InvalidOrder("MIN_NOTIONAL"), ExchangeRejected),
        (ccxt.AuthenticationError("bad key"), AuthenticationFailed),
        (ccxt.PermissionDenied("no trade permission"), AuthenticationFailed),
    ],
)
async def test_order_write_failures_are_classified_conservatively(
    error: Exception, expected: type[Exception]
) -> None:
    exchange, client = _authenticated()
    client.order_error = error
    with pytest.raises(expected):
        await exchange.create_market_order(BUY)


async def test_a_duplicate_client_id_returns_the_existing_order_instead_of_failing() -> None:
    exchange, client = _authenticated()
    client.order_error = ccxt.InvalidOrder("binance Duplicate order sent.")
    client.lookup_response = _buy_response()
    order = await exchange.create_market_order(BUY)
    assert order.status is OrderStatus.FILLED  # idempotent: the first attempt is the order


async def test_writes_are_never_retried_by_the_adapter() -> None:
    exchange, client = _authenticated()
    calls: list[int] = []
    original = client.create_order

    async def counting(*args: Any) -> dict[str, Any]:
        calls.append(1)
        return await original(*args)

    client.create_order = counting  # type: ignore[method-assign]
    client.order_error = ccxt.NetworkError("boom")
    with pytest.raises(UnknownOutcome):
        await exchange.create_market_order(BUY)
    assert len(calls) == 1


# --- credentials ----------------------------------------------------------------------------


async def test_an_integration_without_credentials_cannot_touch_the_account() -> None:
    public = BinanceExchange(FakeCcxtClient())
    for call in (
        public.create_market_order(BUY),
        public.fetch_order(SYMBOL, CID),
        public.cancel_order(SYMBOL, CID),
        public.create_stop_order(StopOrderRequest(CID, SYMBOL, Decimal(1), Decimal(1))),
        public.fetch_open_orders(SYMBOL),
        public.fetch_balances(),
    ):
        with pytest.raises(NotAuthenticated):
            await call
    assert issubclass(NotAuthenticated, TradingNotEnabled)


def test_credentials_never_appear_in_repr_or_str() -> None:
    for text in (repr(CREDENTIALS), str(CREDENTIALS), f"{CREDENTIALS}"):
        assert "test-api-secret-5678" not in text and "test-api-key-1234" not in text
        assert "5678" not in text or "***" in text
