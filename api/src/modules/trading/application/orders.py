"""Order handling against a real exchange (testnet today, live later).

The paper venue fills instantly inside the candle's transaction. A real exchange cannot: a
network call must never sit inside a database transaction, and its outcome can be unknown. So
an order lives in two phases, each its own transaction:

1. **Intent** (committed by the trader together with the candle): the order exists as
   SUBMITTING with its deterministic client order id, and the capital it needs is reserved.
2. **Result**: after the exchange call, whatever the exchange reports is applied to the order,
   the portfolio and the reservation.

If the process dies between the two, or the call times out, the order is left SUBMITTING /
UNKNOWN and the reconciler resolves it by looking the client order id up on the exchange. An
order is never re-sent blindly.
"""

import asyncio
import logging
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager, suppress
from datetime import timedelta
from decimal import Decimal
from uuid import UUID

from core.clock import Clock
from core.ids import IdGenerator
from modules.analytics.domain.metrics import round_trip_pnls
from modules.audit.models import AuditEvent
from modules.bots.domain.models import Bot, BotState, ExecutionMode
from modules.exchanges.application.connections import ConnectionResolver
from modules.exchanges.application.exchange import Exchange
from modules.exchanges.application.ports import MarketOrderRequest, StopOrderRequest, VenueOrder
from modules.exchanges.errors import (
    AuthenticationFailed,
    ExchangeRejected,
    TransientExchangeError,
    UnknownOrder,
)
from modules.execution.domain.normalizer import OrderRejected, normalize_quantity
from modules.execution.domain.orders import (
    Fill,
    InvalidOrderTransition,
    Order,
    OrderStatus,
    make_stop_client_order_id,
)
from modules.portfolio.domain.models import PortfolioState
from modules.risk_management.domain.models import LiveLimits, consecutive_losses_breached
from modules.strategies.domain.types import Side
from modules.trading.application.ports import TradingStore

logger = logging.getLogger(__name__)

TradingStoreFactory = Callable[[], AbstractAsyncContextManager[TradingStore]]


class OrderExecutor:
    def __init__(
        self,
        stores: TradingStoreFactory,
        resolver: ConnectionResolver,
        clock: Clock,
        ids: IdGenerator,
        absent_after: timedelta,
        live_limits: LiveLimits | None = None,
    ) -> None:
        self._stores = stores
        self._resolver = resolver
        self._clock = clock
        self._ids = ids
        self._absent_after = absent_after
        self._live_limits = live_limits or LiveLimits()

    # --- phase 1 (called by the trader inside the candle's transaction) -----------------------

    @staticmethod
    def reserve(order: Order, portfolio: PortfolioState, price: Decimal, fee_rate: Decimal) -> None:
        """Hold the capital the order needs so no other order can spend it."""
        if order.side is Side.BUY:
            order.reserved_cash = order.quantity * price * (1 + fee_rate)
            portfolio.reserve(cash=order.reserved_cash)
        else:
            order.reserved_quantity = order.quantity
            portfolio.reserve(quantity=order.quantity)

    # --- phase 2 -----------------------------------------------------------------------------

    async def submit(self, bot: Bot, order_id: UUID) -> None:
        """Send a SUBMITTING order to the exchange and apply what comes back."""
        try:
            exchange = await self._exchange(bot)
        except Exception as exc:
            await self._reject(bot, order_id, f"exchange unavailable: {exc}")
            raise
        async with self._stores() as store:
            order = await store.orders.get(order_id)
            portfolio = await store.portfolio.get(bot.id)
        if order is None or order.status is not OrderStatus.SUBMITTING:
            return

        # Independent of how the order came to be: no live entry may exceed the hard cap.
        cap = self._live_limits.max_order_notional
        if (
            bot.config.mode is ExecutionMode.LIVE
            and order.side is Side.BUY
            and (cap is None or order.reserved_cash > cap * Decimal("1.02"))
        ):
            await self._reject(bot, order_id, "exceeds the live per-order hard cap")
            return

        stop_cid = portfolio.stop_order_client_id if portfolio is not None else None
        # The resting stop locks the coins: take it off first (or learn it already fired).
        if (
            order.side is Side.SELL
            and stop_cid
            and await self._cancel_native_stop(bot, exchange, stop_cid)
        ):
            await self._reject(bot, order_id, "position already closed by the protective stop")
            return

        request = MarketOrderRequest(
            order.client_order_id, order.symbol, order.side, order.quantity
        )
        order.submitted_at = self._clock.now()
        async with self._stores() as store:  # when it really left for the exchange
            await store.orders.update(order, [])
            await store.commit()
        try:
            # Shielded: if this task is cancelled mid-flight the request still completes, and
            # the reconciler picks the result up from the exchange.
            venue = await asyncio.shield(exchange.create_market_order(request))
        except ExchangeRejected as exc:
            await self._reject(bot, order_id, str(exc))
        except TransientExchangeError as exc:
            await self._reject(bot, order_id, f"not placed: {exc}")
        except AuthenticationFailed as exc:
            await self._reject(bot, order_id, f"credentials rejected: {exc}")
            if bot.config.connection_id is not None:
                await self._resolver.mark_invalid(bot.config.connection_id, str(exc))
            raise
        except Exception as exc:  # UnknownOutcome and anything unforeseen: it may exist
            await self._mark_unknown(bot, order_id, f"{type(exc).__name__}: {exc}")
        else:
            await self._apply(bot, order_id, venue)
            if order.side is Side.BUY and venue.fills:
                await self.ensure_native_stop(bot, order.client_order_id)

    async def resolve(self, bot: Bot, order: Order) -> None:
        """Settle an order whose outcome is unknown, by asking the exchange about it."""
        exchange = await self._exchange(bot)
        venue = await exchange.fetch_order(order.symbol, order.client_order_id)
        if venue is not None:
            await self._apply(bot, order.id, venue)
            if order.side is Side.BUY and venue.fills:
                await self.ensure_native_stop(bot, order.client_order_id)
        elif self._clock.now() - order.created_at >= self._absent_after:
            await self._reject(
                bot, order.id, "never reached the exchange (not found after waiting)"
            )

    # --- native stop-loss --------------------------------------------------------------------

    async def ensure_native_stop(self, bot: Bot, entry_client_order_id: str) -> None:
        """Rest the position's stop-loss on the exchange when it supports that.

        Failing to place it is not fatal: the bot keeps monitoring the stop itself.
        """
        exchange = await self._exchange(bot)
        if not exchange.capabilities.native_stop_orders:
            return
        symbol = bot.config.symbol
        market = await exchange.fetch_market_info(symbol)
        async with self._stores() as store:
            portfolio = await store.portfolio.get(bot.id)
            if (
                portfolio is None
                or portfolio.quantity <= 0
                or portfolio.stop_price is None
                or portfolio.stop_order_client_id is not None
            ):
                return
            try:
                quantity = normalize_quantity(portfolio.quantity, portfolio.stop_price, market)
            except OrderRejected as exc:
                await self._audit(store, bot, "stop.placement_failed", {"reason": str(exc)})
                await store.commit()
                return
            stop = Order(
                id=self._ids.new_id(),
                bot_id=bot.id,
                session_id=(await self._session_id(store, bot)),
                client_order_id=make_stop_client_order_id(entry_client_order_id),
                symbol=symbol,
                side=Side.SELL,
                quantity=quantity,
                bar_time=self._clock.now(),
                created_at=self._clock.now(),
                order_type="stop_loss",
                stop_price=portfolio.stop_price,
                reference_price=portfolio.stop_price,
                submitted_at=self._clock.now(),
            )
            stop_price = portfolio.stop_price
            stop.submit()
            if not await store.orders.add_if_absent(stop):
                return  # already placed (or being resolved): idempotent
            await store.commit()

        request = StopOrderRequest(stop.client_order_id, symbol, quantity, stop_price)
        try:
            venue = await asyncio.shield(exchange.create_stop_order(request))
        except (ExchangeRejected, TransientExchangeError) as exc:
            await self._reject(bot, stop.id, str(exc), event="stop.placement_failed")
        except Exception as exc:
            await self._mark_unknown(bot, stop.id, f"{type(exc).__name__}: {exc}")
        else:
            await self._apply(bot, stop.id, venue)

    async def sync_native_stop(self, bot: Bot) -> None:
        """Notice a stop that fired (or vanished) while we were not looking."""
        async with self._stores() as store:
            portfolio = await store.portfolio.get(bot.id)
        if portfolio is None or portfolio.stop_order_client_id is None:
            return
        exchange = await self._exchange(bot)
        venue = await exchange.fetch_order(bot.config.symbol, portfolio.stop_order_client_id)
        async with self._stores() as store:
            stop = await store.orders.get_by_client_id(bot.id, portfolio.stop_order_client_id)
        if stop is None or venue is None or venue.status in (OrderStatus.OPEN, stop.status):
            return
        await self._apply(bot, stop.id, venue)

    async def _cancel_native_stop(self, bot: Bot, exchange: Exchange, stop_cid: str) -> bool:
        """Cancel the resting stop; True when it had already closed the position."""
        symbol = bot.config.symbol
        with suppress(UnknownOrder, ExchangeRejected):  # already gone or filled: lookup tells which
            await exchange.cancel_order(symbol, stop_cid)
        venue = await exchange.fetch_order(symbol, stop_cid)
        if venue is not None:
            async with self._stores() as store:
                stop = await store.orders.get_by_client_id(bot.id, stop_cid)
            if stop is not None and not stop.is_final:
                await self._apply(bot, stop.id, venue)
        return venue is not None and venue.status is OrderStatus.FILLED

    # --- applying results --------------------------------------------------------------------

    async def _apply(self, bot: Bot, order_id: UUID, venue: VenueOrder) -> None:
        min_quantity = await self._min_quantity(bot)
        async with self._stores() as store:
            order = await store.orders.get(order_id)
            if order is None:
                return
            sold = await self._apply_in_store(store, bot, order, venue, min_quantity)
            if sold:
                pnls = round_trip_pnls(await store.orders.list_fills(bot.id))
                if consecutive_losses_breached(pnls, bot.config.risk):
                    await self._pause(
                        store, bot, "risk.consecutive_losses", "max consecutive losses reached"
                    )
            await store.commit()

    async def _min_quantity(self, bot: Bot) -> Decimal:
        exchange = await self._exchange(bot)
        return (await exchange.fetch_market_info(bot.config.symbol)).min_quantity

    async def _apply_in_store(
        self,
        store: TradingStore,
        bot: Bot,
        order: Order,
        venue: VenueOrder,
        min_quantity: Decimal,
    ) -> bool:
        """Fold the exchange's view of ``order`` into it and the portfolio. True if it sold."""
        portfolio = await store.portfolio.get(bot.id) or PortfolioState.new(
            bot.id, bot.config.initial_capital
        )
        known = {f.trade_id for f in order.fills if f.trade_id}
        new_fills: list[Fill] = [
            f for f in venue.fills if f.trade_id is None or f.trade_id not in known
        ]
        order.exchange_order_id = venue.exchange_order_id or order.exchange_order_id

        applied: list[Fill] = []
        for fill in new_fills:
            if order.is_final:
                break
            order.apply_fill(fill)
            portfolio.apply_fill(fill)
            applied.append(fill)
        if not order.is_final and venue.status is OrderStatus.FILLED:
            order.status = OrderStatus.FILLED  # the exchange says done; trust it over rounding
        elif not applied and venue.status is not order.status:
            target = (
                OrderStatus.OPEN if venue.status is OrderStatus.PARTIALLY_FILLED else venue.status
            )
            try:
                order.transition(target)
            except InvalidOrderTransition:
                logger.warning("ignoring %s -> %s for %s", order.status, target, order.id)

        if order.order_type == "stop_loss":
            if order.status is OrderStatus.OPEN:
                portfolio.stop_order_client_id = order.client_order_id
            elif order.is_final and not order.fills:
                if portfolio.stop_order_client_id == order.client_order_id:
                    portfolio.stop_order_client_id = None
                await self._audit(store, bot, "stop.lost", {"status": order.status.value})
        elif order.side is Side.BUY and applied and portfolio.quantity > 0:
            portfolio.stop_price = order.planned_stop_price
            portfolio.take_profit_price = order.planned_take_profit_price

        if order.is_final:
            portfolio.release(order.reserved_cash, order.reserved_quantity)
            order.reserved_cash = order.reserved_quantity = Decimal(0)
        if any(f.side is Side.SELL for f in applied):
            dust = portfolio.write_off_dust(min_quantity)
            if dust:
                await self._audit(store, bot, "position.dust_written_off", {"quantity": str(dust)})

        await store.orders.update(order, applied)
        await store.portfolio.save(portfolio)
        await self._audit(
            store,
            bot,
            self._event_for(order),
            {
                "client_order_id": order.client_order_id,
                "status": order.status.value,
                "filled_quantity": str(order.filled_quantity),
                "avg_price": None if order.avg_fill_price is None else str(order.avg_fill_price),
            },
        )
        return any(f.side is Side.SELL for f in applied)

    @staticmethod
    def _event_for(order: Order) -> str:
        if order.order_type == "stop_loss":
            return "stop.filled" if order.status is OrderStatus.FILLED else "stop.updated"
        return {
            OrderStatus.FILLED: "order.filled",
            OrderStatus.PARTIALLY_FILLED: "order.partially_filled",
            OrderStatus.CANCELED: "order.canceled",
            OrderStatus.EXPIRED: "order.expired",
        }.get(order.status, "order.updated")

    async def _reject(
        self, bot: Bot, order_id: UUID, reason: str, event: str = "order.rejected"
    ) -> None:
        async with self._stores() as store:
            order = await store.orders.get(order_id)
            if order is None or order.is_final:
                return
            portfolio = await store.portfolio.get(bot.id)
            order.reject(reason)
            if portfolio is not None:
                portfolio.release(order.reserved_cash, order.reserved_quantity)
                await store.portfolio.save(portfolio)
            order.reserved_cash = order.reserved_quantity = Decimal(0)
            await store.orders.update(order, [])
            await self._audit(
                store,
                bot,
                event,
                {"client_order_id": order.client_order_id, "reason": reason},
            )
            await store.commit()

    async def _mark_unknown(self, bot: Bot, order_id: UUID, reason: str) -> None:
        """Keep the capital reserved: the order may be live on the exchange."""
        async with self._stores() as store:
            order = await store.orders.get(order_id)
            if order is None or order.status is not OrderStatus.SUBMITTING:
                return
            order.transition(OrderStatus.UNKNOWN)
            order.reject_reason = reason  # last known cause, kept for the operator
            await store.orders.update(order, [])
            await self._audit(
                store,
                bot,
                "order.unknown",
                {"client_order_id": order.client_order_id, "reason": reason},
            )
            await store.commit()

    # --- helpers -----------------------------------------------------------------------------

    async def _exchange(self, bot: Bot) -> Exchange:
        if bot.config.connection_id is None:
            raise ExchangeRejected("bot has no exchange connection")
        return await self._resolver.exchange_for(bot.config.connection_id)

    async def _session_id(self, store: TradingStore, bot: Bot) -> UUID:
        session = await store.sessions.get_active(bot.id)
        if session is None:
            raise ExchangeRejected("bot has no active session")
        return session.id

    @staticmethod
    async def _audit(
        store: TradingStore, bot: Bot, event_type: str, payload: dict[str, object]
    ) -> None:
        await store.audit.add(
            AuditEvent(
                event_type, "bot", str(bot.id), actor="worker", bot_id=bot.id, payload=payload
            )
        )

    async def _pause(self, store: TradingStore, bot: Bot, event: str, message: str) -> None:
        await store.bots.set_desired(bot.id, BotState.PAUSED)
        await store.bots.set_observed(bot.id, BotState.PAUSED, message)
        await self._audit(store, bot, event, {"reason": message})
