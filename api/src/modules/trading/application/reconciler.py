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
            if bot is None or bot.config.mode is not ExecutionMode.TESTNET:
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
                if b.config.mode is ExecutionMode.TESTNET and b.config.connection_id is not None
            ]
        by_connection: dict[UUID, list[Bot]] = defaultdict(list)
        for bot in bots:
            assert bot.config.connection_id is not None
            by_connection[bot.config.connection_id].append(bot)

        mismatches = 0
        for connection_id, connection_bots in by_connection.items():
            try:
                mismatches += await self._reconcile_connection(connection_id, connection_bots)
            except Exception:
                logger.exception("reconciliation of connection %s failed", connection_id)
        return mismatches

    async def _reconcile_connection(self, connection_id: UUID, bots: list[Bot]) -> int:
        started = self._clock.now()
        async with self._stores() as store:
            for bot in bots:
                if await store.orders.count_unresolved(bot.id):
                    return 0  # books and exchange legitimately differ until those are settled
        exchange = await self._resolver.exchange_for(connection_id)
        balances = await exchange.fetch_balances()

        expected: dict[str, Decimal] = defaultdict(Decimal)
        foreign_orders: set[str] = set()
        open_orders: dict[str, list[str]] = {}
        async with self._stores() as store:
            for bot in bots:
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
            await store.commit()
        if problems:
            logger.error("reconciliation mismatch on connection %s: %s", connection_id, problems)
        return len(problems)
