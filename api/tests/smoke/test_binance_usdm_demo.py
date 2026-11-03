"""Explicitly opt-in smoke test against the Binance USD-M Demo account.

This test places a small order using simulated funds. It is not included in the default suite.
Set the dedicated Demo credentials and the exact acknowledgement flag before running it.
"""

import asyncio
import os
import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from modules.exchanges.application.ports import MarketOrderRequest, StopOrderRequest
from modules.exchanges.domain.connections import Credentials
from modules.exchanges.domain.models import MarginMode, PositionSide, TradingProduct
from modules.exchanges.errors import UnknownOutcome
from modules.exchanges.infrastructure.binance_usdm import BinanceUsdmExchange
from modules.execution.domain.normalizer import normalize_quantity, round_price
from modules.execution.domain.orders import OrderStatus
from modules.market_data.domain.models import MarkPrice
from modules.strategies.domain.types import Side

pytestmark = pytest.mark.smoke
ORDER_LOOKUP_DELAYS = (0.25, 0.5, 1, 2, 4, 8, 14.25)

KEY = os.environ.get("BINANCE_USDM_DEMO_API_KEY")
SECRET = os.environ.get("BINANCE_USDM_DEMO_API_SECRET")
ORDER_SMOKE_ACK = os.environ.get("BINANCE_USDM_DEMO_ORDER_SMOKE") == "I_UNDERSTAND_DEMO_ORDERS"
SYMBOL = os.environ.get("BINANCE_USDM_DEMO_SYMBOL", "BTC/USDT:USDT")
MAX_NOTIONAL = Decimal("50")
LEVERAGE = 2


async def _write_or_resolve(awaitable, exchange: BinanceUsdmExchange, symbol: str, client_id: str):
    try:
        return await awaitable
    except UnknownOutcome:
        # Treat timeouts as ambiguous, not failed. Keep looking up the stable client ID for the
        # same 30-second window used by the application's unknown-order reconciler.
        for delay in ORDER_LOOKUP_DELAYS:
            await asyncio.sleep(delay)
            result = await exchange.fetch_order(symbol, client_id)
            if result is not None:
                return result
        raise


async def _next_order_update(exchange: BinanceUsdmExchange, client_id: str) -> dict[str, object]:
    async for event in exchange.stream_user_events():
        order = event.get("o")
        if (
            event.get("e") == "ORDER_TRADE_UPDATE"
            and isinstance(order, dict)
            and order.get("c") == client_id
        ):
            return event
    raise AssertionError("Binance USD-M Demo user stream ended before the entry update")


async def test_unknown_demo_order_is_looked_up_until_client_id_appears(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    delays: list[float] = []

    async def no_wait(delay: float) -> None:
        delays.append(delay)

    monkeypatch.setattr(asyncio, "sleep", no_wait)

    class Exchange:
        def __init__(self) -> None:
            self.lookups = 0
            self.order = object()

        async def fetch_order(self, _symbol: str, _client_id: str) -> object | None:
            self.lookups += 1
            return self.order if self.lookups == 3 else None

    async def uncertain_write() -> object:
        raise UnknownOutcome("response timed out")

    exchange = Exchange()
    result = await _write_or_resolve(
        uncertain_write(), exchange, "BTC/USDT:USDT", "lcdf-unknown"  # type: ignore[arg-type]
    )

    assert result is exchange.order
    assert exchange.lookups == 3
    assert delays == list(ORDER_LOOKUP_DELAYS[:3])


@pytest.mark.skipif(
    not (KEY and SECRET and ORDER_SMOKE_ACK),
    reason=(
        "requires BINANCE_USDM_DEMO_API_KEY/SECRET and "
        "BINANCE_USDM_DEMO_ORDER_SMOKE=I_UNDERSTAND_DEMO_ORDERS"
    ),
)
@pytest.mark.parametrize("position_side", [PositionSide.LONG, PositionSide.SHORT])
async def test_binance_usdm_demo_order_stop_stream_and_reduce_only_round_trip(
    position_side: PositionSide,
) -> None:
    assert KEY and SECRET and ORDER_SMOKE_ACK
    exchange = BinanceUsdmExchange(
        credentials=Credentials(KEY, SECRET),
        demo=True,
    )
    entry_id = f"lcdf-{uuid.uuid4().hex[:18]}"
    stop_id = f"{entry_id}-sl"
    close_id = f"{entry_id}-close"
    stream_task: asyncio.Task[dict[str, object]] | None = None
    order_submitted = False

    try:
        market = await exchange.fetch_market_info(SYMBOL)
        target_notional = max(Decimal("20"), market.min_notional * Decimal("1.5"))
        if target_notional > MAX_NOTIONAL:
            pytest.skip(
                f"minimum notional for {SYMBOL} exceeds this smoke test's {MAX_NOTIONAL} USDT cap"
            )

        positions = await exchange.fetch_positions([SYMBOL])
        open_orders = await exchange.fetch_open_orders(SYMBOL)
        if positions or open_orders:
            pytest.skip("close existing Demo exposure and cancel its orders before the smoke test")
        await exchange.prepare_market_configuration(
            TradingProduct.LINEAR_PERPETUAL,
            SYMBOL,
            LEVERAGE,
            MarginMode.ISOLATED,
            target_notional,
        )
        mark: MarkPrice = await exchange.fetch_mark_price(SYMBOL)
        mark_age = (datetime.now(UTC) - mark.timestamp).total_seconds()
        assert 0 <= mark_age <= 15, f"Demo mark price is stale or from the future ({mark_age:.1f}s)"
        quantity = normalize_quantity(target_notional / mark.price, mark.price, market)
        actual_notional = quantity * mark.price
        balances = await exchange.fetch_balances()
        usdt = balances.get("USDT")
        required_collateral = actual_notional / LEVERAGE + actual_notional * Decimal("0.01")
        if usdt is None or usdt.free < required_collateral:
            pytest.skip(
                "USD-M Demo account does not have enough free USDT for the capped smoke order"
            )

        # Give the event stream time to establish its Demo listen key and WebSocket before entry.
        stream_task = asyncio.create_task(_next_order_update(exchange, entry_id))
        await asyncio.sleep(1)
        entry_request = MarketOrderRequest(
            entry_id,
            SYMBOL,
            Side.BUY if position_side is PositionSide.LONG else Side.SELL,
            quantity,
            product=TradingProduct.LINEAR_PERPETUAL,
            position_side=position_side,
            leverage=LEVERAGE,
            margin_mode=MarginMode.ISOLATED,
        )
        order_submitted = True
        entry = await _write_or_resolve(
            exchange.create_market_order(entry_request), exchange, SYMBOL, entry_id
        )
        assert entry.filled_quantity > 0
        assert entry.status in {OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED}
        event = await asyncio.wait_for(stream_task, timeout=30)
        stream_task = None
        assert event["e"] == "ORDER_TRADE_UPDATE"

        positions = await exchange.fetch_positions([SYMBOL])
        assert len(positions) == 1
        position = positions[0]
        assert position.side is position_side
        assert position.margin_mode is MarginMode.ISOLATED
        assert position.leverage == LEVERAGE

        current_mark = await exchange.fetch_mark_price(SYMBOL)
        stop_multiplier = Decimal("0.5") if position_side is PositionSide.LONG else Decimal("1.5")
        stop_price = round_price(current_mark.price * stop_multiplier, market)
        stop = await _write_or_resolve(
            exchange.create_stop_order(
                StopOrderRequest(
                    stop_id,
                    SYMBOL,
                    position.quantity,
                    stop_price,
                    side=Side.SELL if position_side is PositionSide.LONG else Side.BUY,
                    product=TradingProduct.LINEAR_PERPETUAL,
                    position_side=position_side,
                    reduce_only=True,
                )
            ),
            exchange,
            SYMBOL,
            stop_id,
        )
        assert stop.status is OrderStatus.OPEN
        open_orders = await exchange.fetch_open_orders(SYMBOL)
        assert any(order.client_order_id == stop_id for order in open_orders)

        canceled = await exchange.cancel_order(SYMBOL, stop_id)
        assert canceled.status is OrderStatus.CANCELED
        position = (await exchange.fetch_positions([SYMBOL]))[0]
        close_side = Side.SELL if position_side is PositionSide.LONG else Side.BUY
        close = await _write_or_resolve(
            exchange.create_market_order(
                MarketOrderRequest(
                    close_id,
                    SYMBOL,
                    close_side,
                    position.quantity,
                    product=TradingProduct.LINEAR_PERPETUAL,
                    position_side=position_side,
                    leverage=LEVERAGE,
                    margin_mode=MarginMode.ISOLATED,
                    reduce_only=True,
                )
            ),
            exchange,
            SYMBOL,
            close_id,
        )
        assert close.filled_quantity > 0
        assert await exchange.fetch_positions([SYMBOL]) == []
        assert await exchange.fetch_open_orders(SYMBOL) == []
    finally:
        try:
            if stream_task is not None:
                stream_task.cancel()
                await asyncio.gather(stream_task, return_exceptions=True)
            if order_submitted:
                # A failed assertion should not leave unmanaged test exposure in Demo.
                cleanup_errors: list[str] = []
                try:
                    open_orders = await exchange.fetch_open_orders(SYMBOL)
                except Exception as exc:
                    cleanup_errors.append(
                        f"could not read open orders during cleanup: {type(exc).__name__}"
                    )
                    open_orders = []
                for order in open_orders:
                    try:
                        await exchange.cancel_order(SYMBOL, order.client_order_id)
                    except Exception as exc:
                        cleanup_errors.append(
                            f"could not confirm cancellation for {order.client_order_id}: "
                            f"{type(exc).__name__}"
                        )
                try:
                    positions_to_close = await exchange.fetch_positions([SYMBOL])
                except Exception as exc:
                    cleanup_errors.append(
                        f"could not read positions during cleanup: {type(exc).__name__}"
                    )
                    positions_to_close = []
                for position in positions_to_close:
                    close_side = Side.SELL if position.side is PositionSide.LONG else Side.BUY
                    client_id = f"{entry_id}-cleanup"
                    try:
                        await _write_or_resolve(
                            exchange.create_market_order(
                                MarketOrderRequest(
                                    client_id,
                                    SYMBOL,
                                    close_side,
                                    position.quantity,
                                    product=TradingProduct.LINEAR_PERPETUAL,
                                    position_side=position.side,
                                    leverage=position.leverage or LEVERAGE,
                                    margin_mode=MarginMode.ISOLATED,
                                    reduce_only=True,
                                )
                            ),
                            exchange,
                            SYMBOL,
                            client_id,
                        )
                    except Exception as exc:
                        cleanup_errors.append(
                            f"could not confirm reduce-only cleanup for {SYMBOL}: "
                            f"{type(exc).__name__}"
                        )
                remaining_positions = await exchange.fetch_positions([SYMBOL])
                remaining_orders = await exchange.fetch_open_orders(SYMBOL)
                if remaining_positions:
                    cleanup_errors.append(f"residual position remains on {SYMBOL}")
                if remaining_orders:
                    cleanup_errors.append(f"open orders remain on {SYMBOL}")
                if cleanup_errors:
                    raise AssertionError("Demo smoke cleanup failed: " + "; ".join(cleanup_errors))
        finally:
            await exchange.aclose()
