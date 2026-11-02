"""Operator initiated, reduce-only close for a Binance USD-M Demo position."""

import logging
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from datetime import timedelta
from decimal import Decimal
from uuid import UUID

from core.clock import Clock
from core.errors import ConflictError, NotFoundError
from core.ids import IdGenerator
from modules.audit.models import AuditEvent
from modules.bots.domain.models import Bot, BotState, ExecutionMode
from modules.exchanges.application.connections import ConnectionResolver
from modules.exchanges.domain.connections import Environment
from modules.exchanges.domain.models import PositionSide, TradingProduct
from modules.execution.domain.fills import simulate_market_fill
from modules.execution.domain.orders import Order
from modules.market_data.domain.models import MarketInfo, MarkPrice
from modules.portfolio.domain.perpetual_ledger import (
    PerpetualLedgerEntry,
    PerpetualLedgerEventKind,
    PerpetualPortfolioSnapshot,
)
from modules.portfolio.domain.perpetuals import LinearPerpetualPosition
from modules.strategies.domain.types import Side
from modules.trading.application.orders import OrderExecutor
from modules.trading.application.ports import TradingStore

logger = logging.getLogger(__name__)
TradingStoreFactory = Callable[[], AbstractAsyncContextManager[TradingStore]]
_MAX_MARK_AGE = timedelta(seconds=15)


class PerpetualCloseService:
    """Pause the bot and close its full Futures position, simulated or on Binance Demo."""

    def __init__(
        self,
        stores: TradingStoreFactory,
        resolver: ConnectionResolver,
        executor: OrderExecutor,
        clock: Clock,
        ids: IdGenerator,
    ) -> None:
        self._stores = stores
        self._resolver = resolver
        self._executor = executor
        self._clock = clock
        self._ids = ids

    async def close(self, bot_id: UUID, *, actor: str, reason: str | None = None) -> Order:
        async with self._stores() as store:
            bot = await store.bots.get(bot_id)
            if bot is None:
                raise NotFoundError(f"bot {bot_id} was not found")
            if bot.config.product is not TradingProduct.LINEAR_PERPETUAL:
                raise ConflictError("manual reduce-only close is only available for Futures bots")
            if (
                bot.config.exchange != "binance-usdm"
                or bot.config.mode not in (ExecutionMode.PAPER, ExecutionMode.TESTNET)
                or bot.config.connection_id is None
            ):
                raise ConflictError("manual Futures close requires a Binance Demo connection")
            ledger = await store.perpetual_portfolio.get(bot.id)
            if ledger is None or ledger.position is None:
                raise ConflictError("there is no open Futures position to close")
            if ledger.reserved_margin > 0 or await store.orders.count_unresolved(bot.id):
                raise ConflictError("resolve pending Futures orders before closing the position")
            position = ledger.position

        connection_id = bot.config.connection_id
        if await self._resolver.environment_for(connection_id) is not Environment.DEMO:
            raise ConflictError("manual Futures close is restricted to Binance Demo")
        exchange = await self._resolver.exchange_for(connection_id)
        fetch_mark = getattr(exchange, "fetch_mark_price", None)
        if not callable(fetch_mark):
            raise ConflictError("the connected exchange does not provide a Futures mark price")
        mark = await fetch_mark(bot.config.symbol)
        now = self._clock.now()
        age = now - mark.timestamp
        if age < timedelta(seconds=-5) or age > _MAX_MARK_AGE:
            raise ConflictError("a fresh Futures mark price is required to close this position")

        if bot.config.mode is ExecutionMode.PAPER:
            market = await exchange.fetch_market_info(bot.config.symbol)
            return await self._close_paper(bot, position, mark, market, actor, reason)

        async with self._stores() as store:
            current = await store.bots.get(bot_id)
            if current is None:
                raise NotFoundError(f"bot {bot_id} was not found")
            if current.config != bot.config:
                raise ConflictError("the bot configuration changed; reload before closing")
            await store.connections.lock(connection_id)
            ledger = await store.perpetual_portfolio.get(bot_id)
            if ledger is None or ledger.position is None:
                raise ConflictError("the Futures position was already closed")
            if (
                ledger.position.side is not position.side
                or ledger.position.quantity != position.quantity
                or ledger.position.leverage != position.leverage
                or ledger.reserved_margin > 0
                or await store.orders.count_unresolved(bot_id)
            ):
                raise ConflictError("the Futures position changed; reconcile before closing")
            session = await store.sessions.get_active(bot.id) or await store.sessions.latest(bot.id)
            if session is None:
                raise ConflictError("the bot has no trading session to attach the close order to")
            close_side = Side.SELL if position.side.value == "long" else Side.BUY
            order = Order(
                id=self._ids.new_id(),
                bot_id=bot.id,
                session_id=session.id,
                client_order_id=f"lc-{self._ids.new_id().hex}",
                symbol=bot.config.symbol,
                side=close_side,
                quantity=position.quantity,
                bar_time=now,
                created_at=now,
                product=TradingProduct.LINEAR_PERPETUAL,
                position_side=position.side,
                leverage=position.leverage,
                reduce_only=True,
                reference_price=mark.price,
            )
            order.submit()
            if not await store.orders.add_if_absent(order):
                raise ConflictError("a close order with this identifier already exists")
            await store.bots.set_desired(bot.id, BotState.PAUSED)
            await store.bots.set_observed(bot.id, BotState.PAUSED, "manual Futures close")
            payload = {
                "client_order_id": order.client_order_id,
                "symbol": order.symbol,
                "side": order.side.value,
                "position_side": position.side.value,
                "quantity": str(position.quantity),
                "mark_price": str(mark.price),
            }
            if reason and reason.strip():
                payload["reason"] = reason.strip()
            await store.audit.add(
                AuditEvent(
                    "futures.manual_close_requested",
                    "bot",
                    str(bot.id),
                    actor=actor,
                    bot_id=bot.id,
                    payload=payload,
                )
            )
            await store.commit()

        try:
            await self._executor.submit(current, order.id)
        except Exception:
            # Submission may have an unknown outcome. The order remains durable for
            # reconciliation, and the route returns its last persisted state.
            logger.exception("manual Futures close submission failed for bot %s", bot_id)
        async with self._stores() as store:
            latest = await store.orders.get(order.id)
            if latest is None:
                raise RuntimeError("manual Futures close order disappeared after submission")
            return latest

    async def _close_paper(
        self,
        bot: Bot,
        expected_position: LinearPerpetualPosition,
        mark: MarkPrice,
        market: MarketInfo,
        actor: str,
        reason: str | None,
    ) -> Order:
        # Kept in a separate transaction from network reads; the ledger row lock serializes this
        # local simulated close with the Futures paper worker.
        connection_id = bot.config.connection_id
        if connection_id is None:
            raise ConflictError("Futures paper close requires its Binance Demo connection")
        async with self._stores() as store:
            current = await store.bots.get(bot.id)
            if current is None:
                raise NotFoundError(f"bot {bot.id} was not found")
            if current.config != bot.config:
                raise ConflictError("the bot configuration changed; reload before closing")
            await store.connections.lock(connection_id)
            ledger = await store.perpetual_portfolio.get(bot.id)
            if ledger is None or ledger.position is None:
                raise ConflictError("there is no open Futures paper position to close")
            position = ledger.position
            if (
                position.side is not expected_position.side
                or position.quantity != expected_position.quantity
                or position.leverage != expected_position.leverage
                or ledger.reserved_margin > 0
                or await store.orders.count_unresolved(bot.id)
            ):
                raise ConflictError("the Futures paper position changed; reload before closing")
            session = await store.sessions.get_active(bot.id) or await store.sessions.latest(bot.id)
            if session is None:
                raise ConflictError("the bot has no trading session to attach the close order to")
            now = self._clock.now()
            snapshots = await store.perpetual_portfolio.list_snapshots(bot.id, limit=1)
            snapshot_at = (
                max(now, snapshots[-1].taken_at + timedelta(microseconds=1)) if snapshots else now
            )
            side = Side.SELL if position.side is PositionSide.LONG else Side.BUY
            fill = simulate_market_fill(
                side,
                position.quantity,
                mark.price,
                bot.config.fee_rate,
                bot.config.slippage_bps,
                market,
                now,
            )
            if fill.quantity != position.quantity:
                raise ConflictError("market quantity rules would leave a Futures paper remainder")
            margin_before = position.isolated_margin
            realized = ledger.close_position(fill.quantity, fill.price, fill.total_fee)
            ledger.mark(mark.price, now, Decimal(0), source="binance_demo_mark_price")
            order = Order(
                id=self._ids.new_id(),
                bot_id=bot.id,
                session_id=session.id,
                client_order_id=f"lc-{self._ids.new_id().hex}",
                symbol=bot.config.symbol,
                side=side,
                quantity=fill.quantity,
                bar_time=now,
                created_at=now,
                product=TradingProduct.LINEAR_PERPETUAL,
                position_side=position.side,
                leverage=position.leverage,
                reduce_only=True,
                reference_price=mark.price,
            )
            order.submit()
            order.apply_fill(fill)
            if not await store.orders.add_if_absent(order):
                raise ConflictError("a Futures paper close order with this identifier exists")
            await store.perpetual_portfolio.append_entry(
                PerpetualLedgerEntry(
                    id=self._ids.new_id(),
                    bot_id=bot.id,
                    occurred_at=now,
                    kind=PerpetualLedgerEventKind.POSITION_REDUCED,
                    wallet_delta=margin_before + realized,
                    isolated_margin_delta=-margin_before,
                    realized_pnl_delta=realized,
                    fee=fill.total_fee,
                    quantity=fill.quantity,
                    side=position.side,
                    price=fill.price,
                    source="paper_fill",
                    external_reference=f"paper:manual-close:{order.client_order_id}",
                )
            )
            await store.perpetual_portfolio.save(ledger)
            await store.perpetual_portfolio.add_snapshot(
                PerpetualPortfolioSnapshot(
                    bot_id=bot.id,
                    session_id=session.id,
                    taken_at=snapshot_at,
                    mark_price=mark.price,
                    wallet_balance=ledger.wallet_balance,
                    isolated_margin=Decimal(0),
                    position_side=None,
                    quantity=Decimal(0),
                    entry_price=Decimal(0),
                    equity=ledger.equity(mark.price),
                    unrealized_pnl=Decimal(0),
                    funding_paid=ledger.funding_paid,
                    funding_received=ledger.funding_received,
                    mark_source="binance_demo_mark_price",
                )
            )
            await store.bots.set_desired(bot.id, BotState.PAUSED)
            await store.bots.set_observed(bot.id, BotState.PAUSED, "manual Futures paper close")
            payload = {
                "client_order_id": order.client_order_id,
                "symbol": order.symbol,
                "side": side.value,
                "position_side": position.side.value,
                "quantity": str(fill.quantity),
                "mark_price": str(mark.price),
                "simulated": True,
            }
            if reason and reason.strip():
                payload["reason"] = reason.strip()
            await store.audit.add(
                AuditEvent(
                    "futures.paper_manual_close",
                    "order",
                    str(order.id),
                    actor=actor,
                    bot_id=bot.id,
                    payload=payload,
                )
            )
            await store.commit()
            return order
