"""Opt-in check of the real Binance spot TESTNET (fake money). Skipped unless keys are provided.

The rest of the suite proves our logic against a simulated exchange; this is the only test that
talks to the real thing, so it is the one that validates the parsing/params assumptions made in
``CcxtExchange`` (order payloads, fees, stop orders, idempotent client ids).

Run it yourself:

    # 1. Create keys at https://testnet.binance.vision (log in with GitHub) -- NOT real keys.
    export TESTNET_API_KEY=...
    export TESTNET_API_SECRET=...
    uv run pytest tests/smoke -m smoke -s

It places a ~15 USDT market buy of BTC, repeats it with the same client id (must not buy
twice), rests and cancels a far-away stop, then sells back. Everything is fake money.
"""

import os
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from modules.exchanges.application.ports import MarketOrderRequest, StopOrderRequest
from modules.exchanges.domain.connections import Credentials
from modules.exchanges.infrastructure.binance import BinanceExchange
from modules.execution.domain.normalizer import normalize_quantity
from modules.execution.domain.orders import OrderStatus
from modules.market_data.domain.models import Timeframe
from modules.strategies.domain.types import Side

pytestmark = pytest.mark.smoke

KEY = os.environ.get("TESTNET_API_KEY")
SECRET = os.environ.get("TESTNET_API_SECRET")
SYMBOL = "BTC/USDT"


@pytest.mark.skipif(not (KEY and SECRET), reason="set TESTNET_API_KEY / TESTNET_API_SECRET")
async def test_binance_testnet_order_round_trip() -> None:
    assert KEY and SECRET
    exchange = BinanceExchange(credentials=Credentials(KEY, SECRET), sandbox=True)
    try:
        market = await exchange.fetch_market_info(SYMBOL)
        balances = await exchange.fetch_balances()
        assert "USDT" in balances, f"testnet account has no USDT: {sorted(balances)}"

        candles = await exchange.fetch_candles(
            SYMBOL, Timeframe.H1, datetime.now(UTC) - timedelta(hours=3), 3
        )
        price = candles[-1].close
        quantity = normalize_quantity(Decimal(15) / price, price, market)

        client_id = f"lc-smoke-{uuid.uuid4().hex[:20]}"
        request = MarketOrderRequest(client_id, SYMBOL, Side.BUY, quantity)
        bought = await exchange.create_market_order(request)
        assert bought.status is OrderStatus.FILLED and bought.fills
        assert bought.filled_quantity == quantity
        print("buy fills:", bought.fills)  # eyeball: fee in BTC (fee_base) or USDT (fee)

        again = await exchange.create_market_order(request)  # idempotent on the client id
        assert again.exchange_order_id == bought.exchange_order_id
        looked_up = await exchange.fetch_order(SYMBOL, client_id)
        assert looked_up is not None and looked_up.status is OrderStatus.FILLED
        assert {f.trade_id for f in looked_up.fills} == {f.trade_id for f in bought.fills}

        received = sum((f.quantity - f.fee_base for f in bought.fills), Decimal(0))
        sellable = normalize_quantity(received, price, market)

        stop_id = f"lc-smoke-{uuid.uuid4().hex[:18]}-sl"
        stop_price = (price * Decimal("0.5") // market.tick_size) * market.tick_size
        stop = await exchange.create_stop_order(
            StopOrderRequest(stop_id, SYMBOL, sellable, stop_price)
        )
        assert stop.status is OrderStatus.OPEN and stop.order_type == "stop_loss"
        assert any(o.client_order_id == stop_id for o in await exchange.fetch_open_orders(SYMBOL))
        cancelled = await exchange.cancel_order(SYMBOL, stop_id)
        assert cancelled.status is OrderStatus.CANCELED

        sold = await exchange.create_market_order(
            MarketOrderRequest(f"lc-smoke-{uuid.uuid4().hex[:20]}", SYMBOL, Side.SELL, sellable)
        )
        assert sold.status is OrderStatus.FILLED
    finally:
        await exchange.aclose()
