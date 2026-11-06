from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from fakes import FakeCcxtClient
from modules.exchanges.application.ports import MarketOrderRequest, StopOrderRequest
from modules.exchanges.domain.connections import Credentials
from modules.exchanges.domain.models import LeverageTier, MarginMode, PositionSide, TradingProduct
from modules.exchanges.errors import ExchangeRejected
from modules.exchanges.infrastructure.binance_usdm import BinanceUsdmExchange
from modules.execution.domain.orders import OrderStatus
from modules.strategies.domain.types import Side

SYMBOL = "BTC/USDT:USDT"
CID = "lc-0123456789abcdef0123456789abcdef"
CREDENTIALS = Credentials("test-api-key-1234", "test-api-secret-5678")


def _exchange() -> tuple[BinanceUsdmExchange, FakeCcxtClient]:
    client = FakeCcxtClient()
    client.order_response = {
        "id": "123",
        "clientOrderId": CID,
        "symbol": SYMBOL,
        "side": "buy",
        "type": "market",
        "status": "closed",
        "amount": 0.01,
        "filled": 0.01,
        "timestamp": 1_700_000_000_000,
        "trades": [],
        "info": {
            "orderId": 123,
            "clientOrderId": CID,
            "status": "FILLED",
            "fills": [
                {
                    "price": "60000",
                    "qty": "0.01",
                    "commission": "0.24",
                    "commissionAsset": "USDT",
                    "tradeId": 456,
                }
            ],
        },
    }
    return BinanceUsdmExchange(client, credentials=CREDENTIALS), client


def _market(**overrides: object) -> dict[str, object]:
    return {
        "symbol": SYMBOL,
        "id": "BTCUSDT",
        "swap": True,
        "linear": True,
        "settle": "USDT",
        "active": True,
        "info": {
            "filters": [
                {"filterType": "PRICE_FILTER", "tickSize": "0.1"},
                {"filterType": "LOT_SIZE", "stepSize": "0.001", "minQty": "0.001"},
                {"filterType": "MIN_NOTIONAL", "notional": "5"},
            ]
        },
        **overrides,
    }


@pytest.mark.parametrize(
    "market",
    [
        _market(swap=False, spot=True),
        _market(linear=False, inverse=True),
        _market(settle="BTC"),
        _market(active=False),
    ],
)
async def test_usdm_market_info_rejects_spot_inactive_and_unsupported_contracts(
    market: dict[str, object],
) -> None:
    exchange = BinanceUsdmExchange(FakeCcxtClient(market))

    with pytest.raises(ExchangeRejected, match="active USDT linear perpetual"):
        await exchange.fetch_market_info(SYMBOL)


async def test_usdm_market_info_accepts_active_usdt_linear_contract() -> None:
    exchange = BinanceUsdmExchange(FakeCcxtClient(_market()))

    info = await exchange.fetch_market_info(SYMBOL)

    assert info.symbol == SYMBOL
    assert info.step_size == Decimal("0.001")


async def test_usdm_open_orders_for_a_symbol_include_normalized_native_stops() -> None:
    exchange, client = _exchange()
    standard = {
        "id": "1",
        "clientOrderId": "entry-order",
        "symbol": SYMBOL,
        "side": "buy",
        "type": "limit",
        "status": "open",
        "amount": "0.01",
        "filled": "0",
        "timestamp": 1_700_000_000_000,
    }
    stop = {**standard, "id": "2", "clientOrderId": "entry-order-sl", "type": "stop_market"}

    async def fetch_open_orders(symbol, since=None, limit=None, params=None):
        return [stop] if params and params.get("trigger") else [standard]

    client.fetch_open_orders = fetch_open_orders  # type: ignore[method-assign]

    orders = await exchange.fetch_open_orders(SYMBOL)

    # Reconciler and supervisor read ``order.client_order_id`` on every item.
    assert [order.client_order_id for order in orders] == ["entry-order", "entry-order-sl"]


async def test_usdm_can_list_open_orders_across_the_account() -> None:
    exchange, client = _exchange()
    calls: list[tuple[object, ...]] = []
    raw = {
        "id": "777",
        "clientOrderId": "manual-order",
        "symbol": SYMBOL,
        "side": "buy",
        "type": "limit",
        "status": "open",
        "amount": "0.01",
        "filled": "0",
        "timestamp": 1_700_000_000_000,
    }

    async def fetch_open_orders(*args: object) -> list[dict[str, object]]:
        calls.append(args)
        return [raw]

    client.fetch_open_orders = fetch_open_orders  # type: ignore[method-assign]

    orders = await exchange.fetch_all_open_orders()

    assert calls == [(None,), (None, None, None, {"trigger": True})]
    assert len(orders) == 2
    assert all(order.symbol == SYMBOL for order in orders)
    assert all(order.client_order_id == "manual-order" for order in orders)


async def test_resuming_a_reconciled_position_does_not_change_its_account_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, client = _exchange()
    exchange = BinanceUsdmExchange(client, credentials=CREDENTIALS, demo=True)
    client.market_data = _market()
    calls: list[str] = []

    async def fetch_balance(params=None):
        calls.append("balance")
        return {"total": {}, "free": {}, "used": {}}

    async def fetch_position_mode():
        calls.append("position_mode")
        return {"hedged": False}

    async def fetch_multi_assets_mode():
        calls.append("multi_assets_mode")
        return {"multiAssetsMargin": False}

    async def fetch_margin_mode(symbol):
        calls.append("margin_mode")
        return {"marginMode": "isolated", "info": {"leverage": "3"}}

    async def set_margin_mode(mode, symbol):
        calls.append("set_margin_mode")

    async def set_leverage(leverage, symbol):
        calls.append("set_leverage")

    async def fetch_positions(symbols):
        calls.append("fetch_positions")
        return [{"contracts": 0.01}]

    monkeypatch.setattr(client, "fetch_balance", fetch_balance, raising=False)
    monkeypatch.setattr(client, "fetch_position_mode", fetch_position_mode, raising=False)
    monkeypatch.setattr(
        client, "fapiPrivateGetMultiAssetsMargin", fetch_multi_assets_mode, raising=False
    )
    monkeypatch.setattr(client, "fetch_margin_mode", fetch_margin_mode, raising=False)
    monkeypatch.setattr(client, "set_margin_mode", set_margin_mode, raising=False)
    monkeypatch.setattr(client, "set_leverage", set_leverage, raising=False)
    monkeypatch.setattr(client, "fetch_positions", fetch_positions, raising=False)

    async def fetch_leverage_tiers(symbol):
        return _supported_tiers()

    monkeypatch.setattr(exchange, "fetch_leverage_tiers", fetch_leverage_tiers)

    async def unexpected_open_orders(symbol):
        calls.append("fetch_open_orders")
        return []

    monkeypatch.setattr(exchange, "fetch_open_orders", unexpected_open_orders)

    await exchange.prepare_market_configuration(
        TradingProduct.LINEAR_PERPETUAL,
        SYMBOL,
        3,
        MarginMode.ISOLATED,
        Decimal("100"),
        allow_existing_exposure=True,
    )

    assert calls == ["balance", "multi_assets_mode", "position_mode", "margin_mode", "margin_mode"]


def _supported_tiers() -> list[LeverageTier]:
    return [LeverageTier(1, Decimal(0), Decimal("1000"), 10, Decimal("0.005"))]


async def test_usdm_fetch_funding_income_preserves_signed_cashflow_and_transaction_id() -> None:
    exchange, client = _exchange()
    client.market_data = _market()
    start = datetime(2025, 1, 1, tzinfo=UTC)
    end = start + timedelta(hours=8)
    client.ledger_response = [
        {
            "id": "9001",
            "code": "USDT",
            "timestamp": int((start + timedelta(hours=4)).timestamp() * 1000),
            "info": {
                "incomeType": "FUNDING_FEE",
                "symbol": "BTCUSDT",
                "income": "-0.12500000",
                "asset": "USDT",
                "time": int((start + timedelta(hours=4)).timestamp() * 1000),
                "tranId": 9001,
            },
        },
        {
            "info": {
                "incomeType": "COMMISSION",
                "symbol": "BTCUSDT",
                "income": "-0.5",
                "asset": "USDT",
                "time": int((start + timedelta(hours=4)).timestamp() * 1000),
                "tranId": 9002,
            },
        },
    ]

    income = await exchange.fetch_funding_income(SYMBOL, start, end)

    assert len(income) == 1
    assert income[0].transaction_id == "9001"
    assert income[0].amount == Decimal("-0.12500000")
    assert income[0].asset == "USDT"
    assert income[0].occurred_at == start + timedelta(hours=4)
    assert client.last_ledger == (
        "USDT",
        int(start.timestamp() * 1000),
        1000,
        {
            "subType": "linear",
            "until": int(end.timestamp() * 1000),
            "incomeType": "FUNDING_FEE",
            "symbol": "BTCUSDT",
        },
    )


@pytest.mark.parametrize(
    ("position", "reduce_only", "side"),
    [
        (PositionSide.LONG, False, Side.BUY),
        (PositionSide.SHORT, False, Side.SELL),
        (PositionSide.LONG, True, Side.SELL),
        (PositionSide.SHORT, True, Side.BUY),
    ],
)
async def test_usdm_market_order_side_and_reduce_only_mapping(
    position: PositionSide, reduce_only: bool, side: Side
) -> None:
    exchange, client = _exchange()

    order = await exchange.create_market_order(
        MarketOrderRequest(
            CID,
            SYMBOL,
            side,
            Decimal("0.01"),
            product=TradingProduct.LINEAR_PERPETUAL,
            position_side=position,
            leverage=3,
            margin_mode=MarginMode.ISOLATED,
            reduce_only=reduce_only,
        )
    )

    assert order.status is OrderStatus.FILLED
    assert client.last_create == (
        SYMBOL,
        "market",
        side.value,
        0.01,
        None,
        {
            "newClientOrderId": CID,
            **({"reduceOnly": True} if reduce_only else {}),
        },
    )


async def test_usdm_short_protective_stop_uses_algo_order_parameters() -> None:
    exchange, client = _exchange()
    client.order_response = {
        "id": "algo-9",
        "clientOrderId": "x-short-sl",
        "symbol": SYMBOL,
        "side": "buy",
        "type": "stop_loss",
        "status": "open",
        "amount": 0.01,
        "filled": 0,
        "timestamp": 1_700_000_000_000,
        "stopPrice": 61000,
        "trades": [],
        "info": {"algoId": "algo-9", "clientAlgoId": "x-short-sl", "algoStatus": "NEW"},
    }

    order = await exchange.create_stop_order(
        StopOrderRequest(
            "x-short-sl",
            SYMBOL,
            Decimal("0.01"),
            Decimal("61000"),
            side=Side.BUY,
            product=TradingProduct.LINEAR_PERPETUAL,
            position_side=PositionSide.SHORT,
            reduce_only=True,
        )
    )

    assert order.status is OrderStatus.OPEN
    assert client.last_create == (
        SYMBOL,
        "market",
        "buy",
        0.01,
        None,
        {
            "newClientOrderId": "x-short-sl",
            "stopPrice": 61000.0,
            "reduceOnly": True,
            "workingType": "MARK_PRICE",
            "isAlgoOrder": True,
        },
    )
    assert exchange.lookup_params("x-short-sl") == {
        "clientAlgoId": "x-short-sl",
        "trigger": True,
    }


class _MarkClient(FakeCcxtClient):
    def __init__(self, payload: dict[str, object]) -> None:
        super().__init__()
        self.payload = payload

    async def fetch_mark_price(self, symbol: str) -> dict[str, object]:
        return self.payload


async def test_fetch_mark_price_reads_the_ccxt_ticker_structure() -> None:
    # Real CCXT 4.5.91 shape for USD-M premiumIndex (captured from the Demo host).
    payload = {
        "symbol": SYMBOL,
        "timestamp": 1793926611000,
        "last": None,
        "markPrice": 2243.85,
        "indexPrice": 2244.47674419,
        "info": {"markPrice": "2243.85000000", "time": "1793926611000"},
    }
    mark = await BinanceUsdmExchange(_MarkClient(payload)).fetch_mark_price(SYMBOL)

    assert mark.price == Decimal("2243.85")
    assert mark.timestamp == datetime.fromtimestamp(1793926611, UTC)


async def test_fetch_mark_price_never_uses_the_last_price() -> None:
    payload = {"symbol": SYMBOL, "timestamp": 1793926611000, "last": 99, "info": {}}

    with pytest.raises(ExchangeRejected):
        await BinanceUsdmExchange(_MarkClient(payload)).fetch_mark_price(SYMBOL)


async def test_canceling_a_native_stop_completes_the_side_missing_from_the_response() -> None:
    # Binance's algo-order cancel response has no side ("none"): real CCXT 4.5.91 behavior.
    class _AlgoClient(FakeCcxtClient):
        async def cancel_order(self, *args):
            self.last_lookup = args
            return {"id": "6612", "clientOrderId": "x-short-sl", "side": "none", "amount": None,
                    "status": "canceled", "type": None}

        async def fetch_order(self, *args):
            return {"id": "6612", "clientOrderId": "x-short-sl", "side": "buy", "amount": "0.013",
                    "type": "stop_market", "stopPrice": "2300", "status": "canceled"}

    client = _AlgoClient()
    client.market_data = _market()
    exchange = BinanceUsdmExchange(client, credentials=CREDENTIALS, demo=True)

    order = await exchange.cancel_order(SYMBOL, "x-short-sl")

    assert order.status is OrderStatus.CANCELED
    assert order.side is Side.BUY
    assert order.quantity == Decimal("0.013")
    assert order.order_type == "stop_loss"


async def test_positions_take_leverage_from_symbol_configuration_when_v3_omits_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Position Information V3 (CCXT 4.5 default) has no "leverage" field: real Demo payload shape.
    _, client = _exchange()
    exchange = BinanceUsdmExchange(client, credentials=CREDENTIALS, demo=True)
    configuration_reads: list[str] = []

    async def fetch_positions(symbols):
        return [
            {
                "symbol": SYMBOL,
                "contracts": 0.013,
                "side": "short",
                "marginMode": "isolated",
                "entryPrice": 2243.85,
                "markPrice": 2243.0,
                "liquidationPrice": 3349.04,
                "notional": 29.18,
                "unrealizedPnl": 0.01,
                "info": {"positionAmt": "-0.013", "isolatedWallet": "14.59"},
            }
        ]

    async def fetch_margin_mode(symbol):
        configuration_reads.append(symbol)
        return {"marginMode": "isolated", "info": {"leverage": "2"}}

    monkeypatch.setattr(client, "fetch_positions", fetch_positions, raising=False)
    monkeypatch.setattr(client, "fetch_margin_mode", fetch_margin_mode, raising=False)

    (position,) = await exchange.fetch_positions([SYMBOL])

    assert position.leverage == 2
    assert configuration_reads == [SYMBOL]


def test_demo_client_does_not_load_currencies_through_sapi() -> None:
    # The Demo hosts have no SAPI: with credentials CCXT would call capital/config/getall during
    # load_markets() and fail with -2008 for a valid Demo key.
    demo = BinanceUsdmExchange(credentials=CREDENTIALS, demo=True)
    live = BinanceUsdmExchange(credentials=CREDENTIALS)

    assert demo._client.options["fetchCurrencies"] is False
    assert live._client.options["fetchCurrencies"] is not False


async def test_installed_ccxt_routes_usdm_stop_to_algo_order_with_expected_fields() -> None:
    import ccxt

    exchange = BinanceUsdmExchange(credentials=CREDENTIALS, demo=True)
    client = exchange._client
    market = _market()
    market.update(
        type="swap",
        spot=False,
        future=False,
        option=False,
        contract=True,
        linear=True,
        inverse=False,
        precision={"amount": 0.001, "price": 0.1},
        limits={
            "amount": {"min": 0.001, "max": 10000},
            "price": {"min": 0.1, "max": 1000000},
        },
    )
    market["info"]["orderTypes"] = ["MARKET", "STOP_MARKET"]
    client.precisionMode = ccxt.TICK_SIZE
    client.markets = {SYMBOL: market}
    client.markets_by_id = {"BTCUSDT": [market]}
    captured: dict[str, object] = {}

    async def algo_order(params: dict[str, object]) -> dict[str, object]:
        captured.update(params)
        return {
            "algoId": 123,
            "clientAlgoId": "x-short-sl",
            "algoStatus": "NEW",
            "symbol": "BTCUSDT",
            "side": "BUY",
            "orderType": "STOP_MARKET",
            "quantity": "0.01",
            "triggerPrice": "110",
            "workingType": "MARK_PRICE",
            "reduceOnly": True,
            "createTime": 1_700_000_000_000,
        }

    async def regular_order(_params: dict[str, object]) -> None:
        raise AssertionError("conditional Futures stop must use the Algo Order endpoint")

    client.fapiPrivatePostAlgoOrder = algo_order
    client.fapiPrivatePostOrder = regular_order
    try:
        venue = await exchange.create_stop_order(
            StopOrderRequest(
                "x-short-sl",
                SYMBOL,
                Decimal("0.01"),
                Decimal("110"),
                side=Side.BUY,
                product=TradingProduct.LINEAR_PERPETUAL,
                position_side=PositionSide.SHORT,
                reduce_only=True,
            )
        )
    finally:
        await exchange.aclose()

    assert captured["algoType"] == "CONDITIONAL"
    assert captured["type"] == "STOP_MARKET"
    assert captured["clientAlgoId"] == "x-short-sl"
    assert captured["triggerPrice"] == "110"
    assert captured["workingType"] == "MARK_PRICE"
    assert captured["reduceOnly"] is True
    assert venue.status is OrderStatus.OPEN
    assert venue.client_order_id == "x-short-sl"
