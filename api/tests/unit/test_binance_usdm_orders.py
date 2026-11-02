from decimal import Decimal

import pytest

from fakes import FakeCcxtClient
from modules.exchanges.application.ports import MarketOrderRequest, StopOrderRequest
from modules.exchanges.domain.connections import Credentials
from modules.exchanges.domain.models import MarginMode, PositionSide, TradingProduct
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
