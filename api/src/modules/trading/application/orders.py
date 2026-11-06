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
import functools
import logging
from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager, suppress
from datetime import datetime, timedelta
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
from modules.exchanges.domain.models import MarginMode, PositionSide, TradingProduct
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
from modules.market_data.domain.models import MarketInfo
from modules.portfolio.domain.models import PortfolioState
from modules.portfolio.domain.perpetual_ledger import PerpetualLedgerEntry, PerpetualLedgerEventKind
from modules.portfolio.domain.perpetuals import PerpetualLedger
from modules.risk_management.domain.models import LiveLimits, consecutive_losses_breached
from modules.strategies.domain.types import Side
from modules.trading.application.bot_locks import hold_bots
from modules.trading.application.ports import TradingStore

logger = logging.getLogger(__name__)

TradingStoreFactory = Callable[[], AbstractAsyncContextManager[TradingStore]]


_STOP_RETRY_DELAYS = (0.5, 1.0)  # a stop that was NOT placed is retried; 3 attempts in all


def _serialized[**P, R](method: Callable[..., Awaitable[R]]) -> Callable[..., Awaitable[R]]:
    """Run an OrderExecutor entry point under the bot's lock (re-entrant for nested calls)."""

    @functools.wraps(method)
    async def wrapper(self: "OrderExecutor", bot: Bot, *args: object, **kwargs: object) -> R:
        async with hold_bots([bot.id]):
            return await method(self, bot, *args, **kwargs)

    return wrapper


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
        # Set by the worker's container: closes a Futures position that has no protective stop.
        self.emergency_close: Callable[[UUID, str], Awaitable[object]] | None = None
        self._stop_retry_delays: tuple[float, ...] = _STOP_RETRY_DELAYS

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

    @staticmethod
    def reserve_perpetual(
        order: Order, ledger: PerpetualLedger, price: Decimal, fee_rate: Decimal
    ) -> None:
        """Reserve isolated collateral for an opening perpetual order before submission."""
        if order.product is not TradingProduct.LINEAR_PERPETUAL:
            raise ValueError("perpetual reservation requires a perpetual order and ledger")
        if order.reserved_margin:
            raise ValueError("order already has a perpetual margin reservation")
        if order.reduce_only:
            if ledger.position is None or order.quantity > ledger.position.quantity:
                raise ValueError("reduce-only order exceeds the open perpetual position")
            return
        if price <= 0 or fee_rate < 0:
            raise ValueError("reservation price and fee rate are invalid")
        order.reserved_margin = order.quantity * price / order.leverage
        order.reserved_margin += order.quantity * price * fee_rate
        ledger.reserve(order.reserved_margin)

    # --- phase 2 -----------------------------------------------------------------------------

    @_serialized
    async def submit(self, bot: Bot, order_id: UUID) -> None:
        """Send a SUBMITTING order to the exchange and apply what comes back."""
        if (
            bot.config.product is TradingProduct.LINEAR_PERPETUAL
            and bot.config.mode is ExecutionMode.LIVE
        ):
            await self._reject(
                bot,
                order_id,
                "USD-M Futures live order execution is not enabled",
                event="risk.futures_live_execution_blocked",
            )
            return
        try:
            exchange = await self._exchange(bot)
        except Exception as exc:
            await self._reject(bot, order_id, f"exchange unavailable: {exc}")
            raise
        async with self._stores() as store:
            order = await store.orders.get(order_id)
            portfolio = await store.portfolio.get(bot.id)
            perpetual = await store.perpetual_portfolio.get(bot.id)
        if order is None or order.status is not OrderStatus.SUBMITTING:
            return

        # Independent of how the order came to be: no live entry may exceed the hard cap.
        cap = self._live_limits.max_order_notional
        opening_order = (
            not order.reduce_only
            if order.product is TradingProduct.LINEAR_PERPETUAL
            else order.side is Side.BUY
        )
        reserved_notional = (
            order.quantity * (order.reference_price or Decimal(0))
            if order.product is TradingProduct.LINEAR_PERPETUAL
            else order.reserved_cash
        )
        if (
            bot.config.mode is ExecutionMode.LIVE
            and opening_order
            and (cap is None or reserved_notional > cap * Decimal("1.02"))
        ):
            await self._reject(bot, order_id, "exceeds the live per-order hard cap")
            return

        stop_cid = (
            portfolio.stop_order_client_id
            if order.product is TradingProduct.SPOT and portfolio is not None
            else (
                perpetual.stop_order_client_id
                if order.product is TradingProduct.LINEAR_PERPETUAL and perpetual is not None
                else None
            )
        )
        # Cancel the resting protective order before a manual close to avoid competing exits.
        if (
            (order.side is Side.SELL if order.product is TradingProduct.SPOT else order.reduce_only)
            and stop_cid
            and order.order_type != "stop_loss"
            and await self._cancel_native_stop(bot, exchange, stop_cid)
        ):
            await self._reject(bot, order_id, "position already closed by the protective stop")
            if order.product is TradingProduct.LINEAR_PERPETUAL:
                await self.ensure_native_stop(bot, order.client_order_id)
            return

        request = MarketOrderRequest(
            order.client_order_id,
            order.symbol,
            order.side,
            order.quantity,
            product=order.product,
            position_side=order.position_side,
            leverage=order.leverage,
            margin_mode=bot.config.margin_mode or MarginMode.ISOLATED,
            reduce_only=order.reduce_only,
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
            if order.product is TradingProduct.LINEAR_PERPETUAL and order.reduce_only:
                await self._restore_perpetual_stop(bot, order.client_order_id)
        except TransientExchangeError as exc:
            await self._reject(bot, order_id, f"not placed: {exc}")
            if order.product is TradingProduct.LINEAR_PERPETUAL and order.reduce_only:
                await self._restore_perpetual_stop(bot, order.client_order_id)
        except AuthenticationFailed as exc:
            await self._reject(bot, order_id, f"credentials rejected: {exc}")
            if bot.config.connection_id is not None:
                await self._resolver.mark_invalid(bot.config.connection_id, str(exc))
            if order.product is TradingProduct.LINEAR_PERPETUAL and order.reduce_only:
                try:
                    await self._restore_perpetual_stop(bot, order.client_order_id)
                except Exception:
                    logger.exception("could not restore the Futures stop after auth failure")
            raise
        except Exception as exc:  # UnknownOutcome and anything unforeseen: it may exist
            await self._mark_unknown(bot, order_id, f"{type(exc).__name__}: {exc}")
            if order.product is TradingProduct.LINEAR_PERPETUAL and order.reduce_only:
                try:
                    await self.resolve(bot, order)
                    await self._restore_perpetual_stop(bot, order.client_order_id)
                except Exception:
                    logger.exception("could not reconcile/restore the Futures stop after timeout")
        else:
            await self._apply(bot, order_id, venue)
            if venue.fills and (
                order.product is TradingProduct.LINEAR_PERPETUAL
                or (order.product is TradingProduct.SPOT and order.side is Side.BUY)
            ):
                await self.ensure_native_stop(bot, order.client_order_id)
    @_serialized
    async def resolve(self, bot: Bot, order: Order) -> None:
        """Settle an order whose outcome is unknown, by asking the exchange about it."""
        exchange = await self._exchange(bot)
        venue = await exchange.fetch_order(order.symbol, order.client_order_id)
        if venue is not None:
            await self._apply(bot, order.id, venue)
            if venue.fills and (
                order.product is TradingProduct.LINEAR_PERPETUAL
                or (order.product is TradingProduct.SPOT and order.side is Side.BUY)
            ):
                await self.ensure_native_stop(bot, order.client_order_id)
        elif self._clock.now() - order.created_at >= self._absent_after:
            await self._reject(
                bot, order.id, "never reached the exchange (not found after waiting)"
            )

    @_serialized
    async def cancel_opening_perpetual_orders(self, bot: Bot) -> int:
        """Cancel this bot's non-reduce-only USD-M orders and apply any racing fills.

        A kill path must not close a position while an entry can still add exposure. Unknown
        order state fails closed; a later worker pass can retry after reconciliation.
        """
        if bot.config.product is not TradingProduct.LINEAR_PERPETUAL:
            return 0
        async with self._stores() as store:
            orders = await store.orders.list_by_bot(bot.id, limit=1000)
        candidates = [
            order
            for order in orders
            if order.product is TradingProduct.LINEAR_PERPETUAL
            and not order.reduce_only
            and not order.is_final
        ]
        exchange = await self._exchange(bot)
        canceled = 0
        for candidate in candidates:
            async with self._stores() as store:
                order = await store.orders.get(candidate.id)
            if order is None or order.is_final:
                continue
            if order.is_unresolved:
                await self.resolve(bot, order)
                async with self._stores() as store:
                    order = await store.orders.get(candidate.id)
                if order is None or order.is_final:
                    continue
                if order.is_unresolved:
                    raise RuntimeError(
                        f"opening order {order.client_order_id} still has unknown outcome"
                    )
            try:
                venue = await exchange.cancel_order(order.symbol, order.client_order_id)
            except Exception as cancel_error:
                resolved = await exchange.fetch_order(order.symbol, order.client_order_id)
                if resolved is None:
                    raise RuntimeError(
                        f"could not confirm cancellation of opening order {order.client_order_id}"
                    ) from cancel_error
                venue = resolved
            await self._apply(bot, order.id, venue)
            if venue.fills:
                await self.ensure_native_stop(bot, order.client_order_id)
            async with self._stores() as store:
                settled = await store.orders.get(order.id)
            if settled is None or not settled.is_final:
                raise RuntimeError(
                    f"opening order {order.client_order_id} remains active after cancellation"
                )
            canceled += 1
        return canceled

    # --- native stop-loss --------------------------------------------------------------------

    @_serialized
    async def ensure_native_stop(self, bot: Bot, entry_client_order_id: str) -> None:
        """Rest the position's stop-loss on the exchange when it supports that.

        Futures cannot fall back to a local-only stop on a worker outage; missing native-stop
        support pauses the bot while leaving the position visible for operator intervention.
        """
        exchange = await self._exchange(bot)
        if not exchange.capabilities.native_stop_orders:
            if bot.config.product is TradingProduct.LINEAR_PERPETUAL:
                async with self._stores() as store:
                    await self._pause(
                        store,
                        bot,
                        "risk.futures_stop_unavailable",
                        "exchange does not support native futures stops",
                    )
                    await store.commit()
            return
        symbol = bot.config.symbol
        try:
            market = await exchange.fetch_market_info(symbol)
        except Exception as exc:
            if bot.config.product is TradingProduct.LINEAR_PERPETUAL:
                async with self._stores() as store:
                    await self._pause(
                        store,
                        bot,
                        "risk.futures_stop_placement_failed",
                        f"could not load market rules for the futures stop: {exc}",
                    )
                    await store.commit()
                return
            raise
        if (
            bot.config.product is TradingProduct.LINEAR_PERPETUAL
            and await self._resize_perpetual_stop(bot, exchange, market)
        ):
            return
        async with self._stores() as store:
            futures = bot.config.product is TradingProduct.LINEAR_PERPETUAL
            portfolio = None if futures else await store.portfolio.get(bot.id)
            ledger = await store.perpetual_portfolio.get(bot.id) if futures else None
            position = ledger.position if ledger is not None else None
            quantity_value = position.quantity if position else (
                portfolio.quantity if portfolio is not None else Decimal(0)
            )
            stop_price = position.stop_price if position else (
                portfolio.stop_price if portfolio is not None else None
            )
            existing_stop = ledger.stop_order_client_id if ledger is not None else (
                portfolio.stop_order_client_id if portfolio is not None else None
            )
            if quantity_value <= 0 or stop_price is None or existing_stop is not None:
                if futures and quantity_value > 0 and stop_price is None:
                    await self._pause(
                        store,
                        bot,
                        "risk.futures_stop_unavailable",
                        "open Futures position has no protective stop price",
                    )
                    await store.commit()
                return
            try:
                quantity = normalize_quantity(quantity_value, stop_price, market)
            except OrderRejected as exc:
                await self._audit(store, bot, "stop.placement_failed", {"reason": str(exc)})
                if futures:
                    await self._pause(
                        store,
                        bot,
                        "risk.futures_stop_placement_failed",
                        "futures protective stop violates market quantity rules",
                    )
                await store.commit()
                return
            if futures:
                if position is None:
                    raise RuntimeError("perpetual position disappeared while placing its stop")
                stop_side = Side.SELL if position.side is PositionSide.LONG else Side.BUY
            else:
                stop_side = Side.SELL
            stop_client_order_id = make_stop_client_order_id(entry_client_order_id)
            previous_stop = await store.orders.get_by_client_id(bot.id, stop_client_order_id)
            if previous_stop is not None:
                if not previous_stop.is_final:
                    return  # unresolved placement: the reconciler owns this client id
                if futures:
                    stop_client_order_id = make_stop_client_order_id(self._ids.new_id().hex)
            stop = Order(
                id=self._ids.new_id(),
                bot_id=bot.id,
                session_id=(await self._session_id(store, bot)),
                client_order_id=stop_client_order_id,
                symbol=symbol,
                side=stop_side,
                quantity=quantity,
                bar_time=self._clock.now(),
                created_at=self._clock.now(),
                product=bot.config.product,
                position_side=position.side if position is not None else None,
                leverage=position.leverage if position is not None else 1,
                reduce_only=futures,
                order_type="stop_loss",
                stop_price=stop_price,
                reference_price=stop_price,
                submitted_at=self._clock.now(),
            )
            stop.submit()
            if not await store.orders.add_if_absent(stop):
                return  # already placed (or being resolved): idempotent
            if futures and ledger is not None:
                ledger.stop_order_client_id = stop.client_order_id
                await store.perpetual_portfolio.save(ledger)
            await store.commit()

        request = StopOrderRequest(
            stop.client_order_id,
            symbol,
            quantity,
            stop_price,
            side=stop.side,
            product=stop.product,
            position_side=stop.position_side,
            reduce_only=stop.reduce_only,
        )
        try:
            venue = await self._create_stop_with_retry(exchange, request)
        except (ExchangeRejected, TransientExchangeError) as exc:
            await self._reject(bot, stop.id, str(exc), event="stop.placement_failed")
        except Exception as exc:
            await self._mark_unknown(bot, stop.id, f"{type(exc).__name__}: {exc}")
        else:
            await self._apply(bot, stop.id, venue)

    async def _create_stop_with_retry(
        self, exchange: Exchange, request: StopOrderRequest
    ) -> VenueOrder:
        """Place the stop, retrying only failures where the exchange definitely did not get it.

        The client order id is stable, so a retry can never create a second stop. A rejection
        (for example "would trigger immediately") is final and is not retried; an unknown
        outcome is not caught here: the reconciler resolves it.
        """
        delays = iter(self._stop_retry_delays)
        while True:
            try:
                return await asyncio.shield(exchange.create_stop_order(request))
            except TransientExchangeError:
                delay = next(delays, None)
                if delay is None:
                    raise
                await asyncio.sleep(delay)

    async def _flatten_unprotected(self, bot: Bot, reason: str) -> None:
        """Close a Futures position whose protective stop could not be placed.

        An unprotected leveraged position is the worst state we can be in, and pausing the bot
        does not protect it. The close is reduce-only through the normal close service.
        """
        if bot.config.product is not TradingProduct.LINEAR_PERPETUAL:
            return
        async with self._stores() as store:
            ledger = await store.perpetual_portfolio.get(bot.id)
            exposed = ledger is not None and ledger.position is not None
        if not exposed:
            return
        if self.emergency_close is None:
            logger.error(
                "bot %s has a Futures position without a stop and no emergency close", bot.id
            )
            return
        try:
            await self.emergency_close(bot.id, f"protective stop failed: {reason}")
        except Exception as exc:
            logger.exception("emergency close failed for bot %s", bot.id)
            async with self._stores() as store:
                await self._audit(
                    store,
                    bot,
                    "risk.futures_unprotected_position",
                    {"reason": reason, "close_error": f"{type(exc).__name__}: {exc}"},
                )
                await store.commit()

    async def _resize_perpetual_stop(
        self, bot: Bot, exchange: Exchange, market: MarketInfo
    ) -> bool:
        """Replace a native stop when a partial fill changes the protected position size."""
        async with self._stores() as store:
            ledger = await store.perpetual_portfolio.get(bot.id)
            if ledger is None or ledger.position is None or ledger.stop_order_client_id is None:
                return False
            position = ledger.position
            stop_id = ledger.stop_order_client_id
            tracked = await store.orders.get_by_client_id(bot.id, stop_id)
            if tracked is None:
                await self._pause(
                    store,
                    bot,
                    "risk.futures_stop_unavailable",
                    "tracked Futures stop is missing from the local order ledger",
                )
                await store.commit()
                return True
            if position.stop_price is None:
                await self._pause(
                    store,
                    bot,
                    "risk.futures_stop_unavailable",
                    "open Futures position has no protective stop price",
                )
                await store.commit()
                return True
            try:
                quantity = normalize_quantity(position.quantity, position.stop_price, market)
            except OrderRejected as exc:
                await self._pause(
                    store,
                    bot,
                    "risk.futures_stop_placement_failed",
                    f"updated Futures stop violates market quantity rules: {exc}",
                )
                await store.commit()
                return True
            if (
                not tracked.is_final
                and tracked.quantity == quantity
                and tracked.stop_price == position.stop_price
            ):
                return True

        await self._cancel_native_stop(bot, exchange, stop_id)
        async with self._stores() as store:
            ledger = await store.perpetual_portfolio.get(bot.id)
            stop_still_tracked = ledger is not None and ledger.stop_order_client_id == stop_id
            position_remains = ledger is not None and ledger.position is not None
            if stop_still_tracked:
                await self._pause(
                    store,
                    bot,
                    "risk.futures_stop_unavailable",
                    "Binance did not confirm cancellation of the outdated Futures stop",
                )
                await store.commit()
                return True
        if position_remains:
            # Canceled client ids are immutable; a replacement gets a fresh id and is committed
            # before its network request so a restart can resolve the same order safely.
            await self.ensure_native_stop(bot, self._ids.new_id().hex)
        return True

    async def _restore_perpetual_stop(self, bot: Bot, client_order_id: str) -> None:
        async with self._stores() as store:
            ledger = await store.perpetual_portfolio.get(bot.id)
            has_position = ledger is not None and ledger.position is not None
            stop_missing = ledger is not None and ledger.stop_order_client_id is None
        if has_position and stop_missing:
            await self.ensure_native_stop(bot, client_order_id)

    @_serialized
    async def sync_native_stop(self, bot: Bot) -> None:
        """Notice a stop that fired (or vanished) while we were not looking."""
        async with self._stores() as store:
            if bot.config.product is TradingProduct.LINEAR_PERPETUAL:
                ledger = await store.perpetual_portfolio.get(bot.id)
                stop_cid = ledger.stop_order_client_id if ledger is not None else None
            else:
                portfolio = await store.portfolio.get(bot.id)
                stop_cid = portfolio.stop_order_client_id if portfolio is not None else None
        if stop_cid is None:
            return
        exchange = await self._exchange(bot)
        venue = await exchange.fetch_order(bot.config.symbol, stop_cid)
        if venue is None and bot.config.product is TradingProduct.LINEAR_PERPETUAL:
            async with self._stores() as store:
                await self._pause(
                    store,
                    bot,
                    "risk.futures_stop_unavailable",
                    "exchange no longer reports the tracked protective futures stop",
                )
                await store.commit()
            return
        async with self._stores() as store:
            stop = await store.orders.get_by_client_id(bot.id, stop_cid)
        if stop is None or venue is None or venue.status in (OrderStatus.OPEN, stop.status):
            return
        await self._apply(bot, stop.id, venue)
        if (
            bot.config.product is TradingProduct.LINEAR_PERPETUAL
            and venue.status in (OrderStatus.CANCELED, OrderStatus.EXPIRED, OrderStatus.REJECTED)
        ):
            await self.ensure_native_stop(bot, stop.client_order_id)

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
        return venue is not None and (
            venue.status is OrderStatus.FILLED or venue.filled_quantity > 0
        )

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
        if order.product is TradingProduct.LINEAR_PERPETUAL:
            return await self._apply_perpetual_fills(store, bot, order, venue)

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

    async def _apply_perpetual_fills(
        self, store: TradingStore, bot: Bot, order: Order, venue: VenueOrder
    ) -> bool:
        """Apply futures executions to the isolated ledger, never to the Spot portfolio."""
        if (
            venue.client_order_id != order.client_order_id
            or venue.symbol != order.symbol
        ):
            raise RuntimeError("exchange response does not match the perpetual order intent")
        ledger = await store.perpetual_portfolio.get(bot.id)
        if ledger is None:
            raise RuntimeError("perpetual portfolio has not been initialized")
        known_ids = {fill.trade_id for fill in order.fills if fill.trade_id is not None}
        known_signatures = {
            (fill.time, fill.side, fill.quantity, fill.price, fill.fee, fill.fee_base)
            for fill in order.fills
        }
        new_fills = [
            fill for fill in venue.fills
            if (fill.trade_id is not None and fill.trade_id not in known_ids)
            or (fill.trade_id is None and
                (fill.time, fill.side, fill.quantity, fill.price, fill.fee, fill.fee_base)
                not in known_signatures)
        ]
        order.exchange_order_id = venue.exchange_order_id or order.exchange_order_id
        applied: list[Fill] = []
        for fill in new_fills:
            if order.is_final:
                break
            if fill.side is not order.side:
                raise RuntimeError("perpetual fill side does not match its order intent")
            fill_reference = (
                f"order:{order.client_order_id}:trade:{fill.trade_id}"
                if fill.trade_id
                else (
                    f"order:{order.client_order_id}:fill:{fill.time.isoformat()}:"
                    f"{fill.quantity}:{fill.price}"
                )
            )
            if order.reserved_margin:
                consumed = min(
                    order.reserved_margin,
                    fill.notional / order.leverage + fill.total_fee,
                )
                ledger.release(consumed)
                order.reserved_margin -= consumed
                await self._append_margin_release(
                    store,
                    bot,
                    consumed,
                    fill.time,
                    f"{fill_reference}:margin-release",
                )
            order.apply_fill(fill)
            side = order.position_side
            if side is None:
                raise RuntimeError("perpetual order has no position side")
            fee = fill.total_fee
            if order.reduce_only:
                position = ledger.position
                if position is None or position.side is not side:
                    raise RuntimeError(
                        "reduce-only fill does not match the open perpetual position"
                    )
                released = position.isolated_margin * fill.quantity / position.quantity
                realized = ledger.close_position(fill.quantity, fill.price, fee)
                kind = PerpetualLedgerEventKind.POSITION_REDUCED
                wallet_delta = released + realized
                margin_delta = -released
                pnl_delta = realized
            else:
                existing = ledger.position
                if existing is None:
                    ledger.open_position(
                        side,
                        fill.quantity,
                        fill.price,
                        order.leverage,
                        fee,
                        order.planned_stop_price,
                        order.planned_take_profit_price,
                    )
                    kind = PerpetualLedgerEventKind.POSITION_OPENED
                else:
                    ledger.increase_position(side, fill.quantity, fill.price, order.leverage, fee)
                    kind = PerpetualLedgerEventKind.POSITION_INCREASED
                wallet_delta = -(fill.notional / order.leverage + fee)
                margin_delta = fill.notional / order.leverage
                pnl_delta = Decimal(0)
            inserted = await store.perpetual_portfolio.append_entry(
                PerpetualLedgerEntry(
                    id=self._ids.new_id(), bot_id=bot.id, occurred_at=fill.time, kind=kind,
                    wallet_delta=wallet_delta, isolated_margin_delta=margin_delta,
                    realized_pnl_delta=pnl_delta, fee=fee, quantity=fill.quantity,
                    side=side, price=fill.price, source="exchange_fill",
                    external_reference=fill_reference,
                )
            )
            if not inserted:
                raise RuntimeError("duplicate perpetual fill ledger entry")
            applied.append(fill)

        if not order.is_final and venue.status is not order.status:
            target = (
                OrderStatus.OPEN
                if venue.status is OrderStatus.PARTIALLY_FILLED and not order.filled_quantity
                else venue.status
            )
            try:
                order.transition(target)
            except InvalidOrderTransition:
                logger.warning("ignoring %s -> %s for %s", order.status, target, order.id)
        if order.order_type == "stop_loss":
            if order.is_final and ledger.stop_order_client_id == order.client_order_id:
                ledger.stop_order_client_id = None
            elif not order.is_final:
                ledger.stop_order_client_id = order.client_order_id
        if order.is_final and order.reserved_margin:
            released = order.reserved_margin
            ledger.release(released)
            await self._append_margin_release(
                store,
                bot,
                released,
                self._clock.now(),
                f"order:{order.client_order_id}:margin-release:terminal",
            )
            order.reserved_margin = Decimal(0)
        await store.perpetual_portfolio.save(ledger)
        await store.orders.update(order, applied)
        await self._audit(store, bot, self._event_for(order), {
            "client_order_id": order.client_order_id,
            "product": order.product.value,
            "position_side": order.position_side.value if order.position_side else None,
            "status": order.status.value,
            "filled_quantity": str(order.filled_quantity),
            "avg_price": None if order.avg_fill_price is None else str(order.avg_fill_price),
        })
        return order.reduce_only and bool(applied)

    async def _append_margin_release(
        self,
        store: TradingStore,
        bot: Bot,
        amount: Decimal,
        occurred_at: datetime,
        external_reference: str,
    ) -> None:
        if amount <= 0:
            return
        inserted = await store.perpetual_portfolio.append_entry(
            PerpetualLedgerEntry(
                id=self._ids.new_id(),
                bot_id=bot.id,
                occurred_at=occurred_at,
                kind=PerpetualLedgerEventKind.MARGIN_RELEASED,
                reserved_margin_delta=-amount,
                source="exchange_order",
                external_reference=external_reference,
            )
        )
        if not inserted:
            raise RuntimeError("duplicate perpetual margin release event")

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
        unprotected = False
        async with self._stores() as store:
            order = await store.orders.get(order_id)
            if order is None or order.is_final:
                return
            order.reject(reason)
            if order.product is TradingProduct.LINEAR_PERPETUAL:
                ledger = await store.perpetual_portfolio.get(bot.id)
                if ledger is not None and order.reserved_margin:
                    released = order.reserved_margin
                    ledger.release(released)
                    await self._append_margin_release(
                        store,
                        bot,
                        released,
                        self._clock.now(),
                        f"order:{order.client_order_id}:margin-release:rejected",
                    )
                    await store.perpetual_portfolio.save(ledger)
                if (
                    ledger is not None
                    and order.order_type == "stop_loss"
                    and ledger.stop_order_client_id == order.client_order_id
                ):
                    ledger.stop_order_client_id = None
                    await store.perpetual_portfolio.save(ledger)
                    unprotected = ledger.position is not None
                    await self._pause(
                        store,
                        bot,
                        "risk.futures_stop_placement_failed",
                        f"native futures stop was rejected: {reason}",
                    )
                order.reserved_margin = Decimal(0)
            else:
                portfolio = await store.portfolio.get(bot.id)
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
        if unprotected:
            await self._flatten_unprotected(bot, reason)

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
