"""Reconciliation: keep our books honest against the exchange.

Two jobs:

* **Resolve pending orders.** Orders left SUBMITTING / UNKNOWN (a timeout, a crash between the
  intent and the call) are looked up by client order id and settled. Nothing is re-sent.
* **Check the account.** All bots on a connection are virtual sub-accounts of one exchange
  account, so the account must hold *at least* what the bots believe they own. Holding more is
  fine (unallocated funds); holding less, or finding a foreign order carrying our id prefix,
  means the books are wrong, so the affected bots are paused and the run is recorded.
"""

import logging
from collections import defaultdict
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from decimal import Decimal
from typing import Any
from uuid import UUID

from core.clock import Clock
from modules.audit.models import AuditEvent
from modules.bots.domain.models import Bot, BotState, ExecutionMode
from modules.exchanges.application.connections import ConnectionResolver
from modules.exchanges.domain.models import TradingProduct
from modules.exchanges.errors import AuthenticationFailed
from modules.trading.application.orders import OrderExecutor
from modules.trading.application.ports import TradingStore

logger = logging.getLogger(__name__)

TradingStoreFactory = Callable[[], AbstractAsyncContextManager[TradingStore]]

OUR_ORDER_PREFIX = "lc-"
_ABSOLUTE_TOLERANCE = Decimal("0.00000001")
_RELATIVE_TOLERANCE = Decimal("0.000001")


class Reconciler:
    def __init__(
        self,
        stores: TradingStoreFactory,
        resolver: ConnectionResolver,
        executor: OrderExecutor,
        clock: Clock,
    ) -> None:
        self._stores = stores
        self._resolver = resolver
        self._executor = executor
        self._clock = clock

    async def resolve_pending(self) -> int:
        """Settle every order whose outcome is unknown. Returns how many were examined."""
        async with self._stores() as store:
            pending = await store.orders.list_unresolved()
            bots = {b.id: b for b in await store.bots.list_bots(500)}
        examined = 0
        for order in pending:
            bot = bots.get(order.bot_id)
            if bot is None or not bot.config.mode.uses_exchange:
                continue
            try:
                await self._executor.resolve(bot, order)
                examined += 1
            except Exception:
                logger.exception("could not resolve order %s", order.client_order_id)
        return examined

    async def reconcile_accounts(self) -> int:
        """Check each connection used by a testnet bot. Returns the number of mismatches."""
        async with self._stores() as store:
            bots = [
                b
                for b in await store.bots.list_bots(500)
                if b.config.mode.uses_exchange and b.config.connection_id is not None
            ]
        by_connection: dict[UUID, list[Bot]] = defaultdict(list)
        for bot in bots:
            assert bot.config.connection_id is not None
            by_connection[bot.config.connection_id].append(bot)

        mismatches = 0
        for connection_id, connection_bots in by_connection.items():
            try:
                mismatches += await self._reconcile_connection(connection_id, connection_bots)
            except Exception as exc:
                logger.exception("reconciliation of connection %s failed", connection_id)
                if any(
                    bot.config.product is TradingProduct.LINEAR_PERPETUAL
                    for bot in connection_bots
                ):
                    await self._reconciliation_unavailable(connection_id, connection_bots, exc)
        return mismatches

    async def _reconciliation_unavailable(
        self, connection_id: UUID, bots: list[Bot], error: Exception
    ) -> None:
        """Pause futures when REST cannot establish the exchange position as authority."""
        futures = [
            bot for bot in bots if bot.config.product is TradingProduct.LINEAR_PERPETUAL
        ]
        started = self._clock.now()
        error_type = type(error).__name__
        async with self._stores() as store:
            await store.reconciliations.add(
                connection_id,
                started,
                "mismatch",
                {
                    "kind": "unavailable",
                    "error_type": error_type,
                    "bots": [str(bot.id) for bot in futures],
                },
            )
            for bot in futures:
                await store.bots.set_desired(bot.id, BotState.PAUSED)
                await store.bots.set_observed(
                    bot.id, BotState.PAUSED, "futures reconciliation unavailable"
                )
                await store.audit.add(
                    AuditEvent(
                        "reconciliation.unavailable",
                        "bot",
                        str(bot.id),
                        actor="worker",
                        bot_id=bot.id,
                        payload={"error_type": error_type},
                    )
                )
            await store.commit()

    async def _reconcile_connection(self, connection_id: UUID, bots: list[Bot]) -> int:
        started = self._clock.now()
        async with self._stores() as store:
            for bot in bots:
                if await store.orders.count_unresolved(bot.id):
                    return 0  # books and exchange legitimately differ until those are settled
        exchange = await self._resolver.exchange_for(connection_id)
        futures_bots = [
            bot for bot in bots if bot.config.product is TradingProduct.LINEAR_PERPETUAL
        ]
        futures_symbols = sorted({bot.config.symbol for bot in futures_bots})
        try:
            balances = await exchange.fetch_balances()
            remote_positions = (
                await exchange.fetch_positions(futures_symbols) if futures_symbols else []
            )
        except AuthenticationFailed as exc:
            await self._credentials_rejected(connection_id, bots, str(exc))
            return 1

        expected: dict[str, Decimal] = defaultdict(Decimal)
        foreign_orders: set[str] = set()
        open_orders: dict[str, list[str]] = {}
        async with self._stores() as store:
            for bot in bots:
                if bot.config.product is TradingProduct.LINEAR_PERPETUAL:
                    continue  # futures collateral is isolated from the spot asset ledger
                portfolio = await store.portfolio.get(bot.id)
                if portfolio is None:
                    continue
                base, _, quote = bot.config.symbol.partition("/")
                expected[quote] += portfolio.cash
                expected[base] += portfolio.quantity
        symbols = {b.config.symbol for b in bots}
        for symbol in symbols:
            open_orders[symbol] = [
                o.client_order_id for o in await exchange.fetch_open_orders(symbol)
            ]
        async with self._stores() as store:
            for bot in bots:
                for cid in open_orders.get(bot.config.symbol, []):
                    if cid.startswith(OUR_ORDER_PREFIX) and (
                        await store.orders.get_by_client_id(bot.id, cid) is None
                    ):
                        foreign_orders.add(cid)  # carries our prefix but we have no record

        problems: list[dict[str, Any]] = []
        for asset, wanted in expected.items():
            held = balances[asset].total if asset in balances else Decimal(0)
            tolerance = max(_ABSOLUTE_TOLERANCE, wanted * _RELATIVE_TOLERANCE)
            if held + tolerance < wanted:
                problems.append(
                    {
                        "kind": "balance_shortfall",
                        "asset": asset,
                        "bots_expect": str(wanted),
                        "exchange_holds": str(held),
                    }
                )
        remote_by_symbol: dict[str, list[Any]] = defaultdict(list)
        for position in remote_positions:
            remote_by_symbol[position.symbol].append(position)
        futures_by_symbol = {bot.config.symbol: bot for bot in futures_bots}
        async with self._stores() as store:
            for symbol, bot in futures_by_symbol.items():
                remote = remote_by_symbol.pop(symbol, [])
                ledger = await store.perpetual_portfolio.get(bot.id)
                local = ledger.position if ledger is not None else None
                if len(remote) > 1:
                    problems.append(
                        {"kind": "multiple_exchange_positions", "symbol": symbol}
                    )
                    continue
                if local is None and not remote:
                    continue
                if local is None:
                    problems.append(
                        {
                            "kind": "untracked_exchange_position",
                            "symbol": symbol,
                            "side": remote[0].side.value,
                            "quantity": str(remote[0].quantity),
                        }
                    )
                    continue
                if not remote:
                    problems.append(
                        {
                            "kind": "exchange_position_missing",
                            "symbol": symbol,
                            "side": local.side.value,
                            "quantity": str(local.quantity),
                        }
                    )
                    continue
                actual = remote[0]
                quantity_tolerance = max(
                    _ABSOLUTE_TOLERANCE, local.quantity * _RELATIVE_TOLERANCE
                )
                differences: dict[str, Any] = {}
                if actual.side is not local.side:
                    differences.update(
                        expected_side=local.side.value, exchange_side=actual.side.value
                    )
                if abs(actual.quantity - local.quantity) > quantity_tolerance:
                    differences.update(
                        expected_quantity=str(local.quantity),
                        exchange_quantity=str(actual.quantity),
                    )
                if actual.entry_price is None or abs(actual.entry_price - local.entry_price) > max(
                    _ABSOLUTE_TOLERANCE, local.entry_price * _RELATIVE_TOLERANCE
                ):
                    differences.update(
                        expected_entry_price=str(local.entry_price),
                        exchange_entry_price=(
                            str(actual.entry_price) if actual.entry_price is not None else None
                        ),
                    )
                if actual.leverage is not None and actual.leverage != local.leverage:
                    differences.update(
                        expected_leverage=local.leverage, exchange_leverage=actual.leverage
                    )
                if actual.margin_mode is not None and actual.margin_mode.value != "isolated":
                    differences["exchange_margin_mode"] = actual.margin_mode.value
                if actual.mark_price is None:
                    differences["exchange_mark_price"] = "unavailable"
                if differences:
                    problems.append(
                        {"kind": "futures_position_mismatch", "symbol": symbol, **differences}
                    )
                    continue
                if ledger is not None and actual.mark_price is not None:
                    notional = actual.notional or actual.quantity * actual.mark_price
                    tiers = await exchange.fetch_leverage_tiers(symbol)
                    tier = next(
                        (
                            item
                            for item in tiers
                            if item.min_notional <= notional < item.max_notional
                            and item.max_leverage >= local.leverage
                        ),
                        None,
                    )
                    if tier is None:
                        problems.append(
                            {
                                "kind": "futures_leverage_tier_unavailable",
                                "symbol": symbol,
                                "notional": str(notional),
                                "leverage": local.leverage,
                            }
                        )
                        continue
                    ledger.mark(
                        actual.mark_price,
                        self._clock.now(),
                        tier.maintenance_margin_rate,
                        source="binance_exchange_mark_price",
                    )
                    ledger.exchange_liquidation_price = actual.liquidation_price
                    ledger.exchange_position_id = symbol
                    ledger.reconciled_at = self._clock.now()
                    await store.perpetual_portfolio.save(ledger)
        for symbol, positions in remote_by_symbol.items():
            for position in positions:
                problems.append(
                    {
                        "kind": "unowned_exchange_position",
                        "symbol": symbol,
                        "side": position.side.value,
                        "quantity": str(position.quantity),
                    }
                )
        for cid in sorted(foreign_orders):
            problems.append({"kind": "unknown_open_order", "client_order_id": cid})

        status = "mismatch" if problems else "ok"
        async with self._stores() as store:
            await store.reconciliations.add(
                connection_id,
                started,
                status,
                {"problems": problems, "bots": [str(b.id) for b in bots]},
            )
            if problems:
                for bot in bots:
                    await store.bots.set_desired(bot.id, BotState.PAUSED)
                    await store.bots.set_observed(
                        bot.id, BotState.PAUSED, "reconciliation mismatch"
                    )
                    await store.audit.add(
                        AuditEvent(
                            "reconciliation.mismatch",
                            "bot",
                            str(bot.id),
                            actor="worker",
                            bot_id=bot.id,
                            payload={"problems": problems},
                        )
                    )
                if any(b.config.mode is ExecutionMode.LIVE for b in bots):
                    reason = "reconciliation mismatch on a live connection"
                    await store.flags.set_kill_switch(True, reason)
                    await store.audit.add(
                        AuditEvent(
                            "system.kill_switch_activated",
                            "system",
                            "kill_switch",
                            actor="worker",
                            payload={"reason": reason},
                        )
                    )
            await store.commit()
        if problems:
            logger.error("reconciliation mismatch on connection %s: %s", connection_id, problems)
        return len(problems)

    async def _credentials_rejected(
        self, connection_id: UUID, bots: list[Bot], reason: str
    ) -> None:
        """The exchange refused the keys (typo, revoked, wrong environment): stop everything
        that depends on them instead of failing on the first real order."""
        await self._resolver.mark_invalid(connection_id, reason)
        message = "exchange credentials rejected"
        async with self._stores() as store:
            for bot in bots:
                await store.bots.set_desired(bot.id, BotState.PAUSED)
                await store.bots.set_observed(bot.id, BotState.ERROR, message)
                await store.audit.add(
                    AuditEvent(
                        "bot.error",
                        "bot",
                        str(bot.id),
                        actor="worker",
                        bot_id=bot.id,
                        payload={"error": message, "detail": reason[:200]},
                    )
                )
            await store.commit()
        logger.error("connection %s rejected by the exchange: %s", connection_id, reason)
