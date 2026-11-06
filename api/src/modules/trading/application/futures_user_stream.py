"""Private Binance USD-M Demo stream lifecycle and fail-closed reconciliation."""

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from uuid import UUID

from core.clock import Clock
from core.errors import DomainError
from modules.audit.models import AuditEvent
from modules.bots.domain.models import Bot, BotState, ExecutionMode
from modules.exchanges.application.connections import ConnectionResolver
from modules.exchanges.application.exchange import Exchange
from modules.exchanges.application.ports import FundingIncome
from modules.exchanges.domain.models import TradingProduct
from modules.portfolio.application.perpetual_ledger_service import PerpetualLedgerService
from modules.portfolio.domain.perpetual_ledger import PerpetualLedgerEventKind
from modules.trading.application.orders import OrderExecutor
from modules.trading.application.reconciler import Reconciler
from modules.trading.application.trader import TradingStoreFactory

logger = logging.getLogger(__name__)
ACCOUNT_WIDE_ORDER_SCAN_SECONDS = 60.0
# Binance disconnects a private socket after 24 h; an end after ~23 h is the scheduled one.
PLANNED_STREAM_END_SECONDS = 23 * 3600.0


def _is_active(bot: Bot) -> bool:
    """A stop request remains active until the worker confirms the observed STOPPED state."""
    return bot.desired_state is not BotState.STOPPED or bot.observed_state is not BotState.STOPPED


class FuturesUserStreamMonitor:
    """Keep a private stream for every configured USD-M Demo bot connection.

    A stream gap pauses affected Futures bots and runs REST reconciliation before reconnecting.
    Recovery never resumes a bot automatically; an operator must review and start it again.
    """

    def __init__(
        self,
        stores: TradingStoreFactory,
        resolver: ConnectionResolver,
        reconciler: Reconciler,
        executor: OrderExecutor,
        clock: Clock,
    ) -> None:
        self._stores = stores
        self._resolver = resolver
        self._reconciler = reconciler
        self._executor = executor
        self._clock = clock
        self._tasks: dict[UUID, asyncio.Task[None]] = {}

    async def ensure_running(self) -> None:
        async with self._stores() as store:
            bots = await store.bots.list_active()
        connection_ids = {
            bot.config.connection_id
            for bot in bots
            if bot.config.product is TradingProduct.LINEAR_PERPETUAL
            and bot.config.mode is ExecutionMode.TESTNET
            and bot.config.connection_id is not None
        }
        for connection_id in connection_ids:
            task = self._tasks.get(connection_id)
            if task is None or task.done():
                self._tasks[connection_id] = asyncio.create_task(
                    self._run_connection(connection_id),
                    name=f"binance-usdm-user-stream-{connection_id}",
                )
        for connection_id, task in tuple(self._tasks.items()):
            if connection_id not in connection_ids:
                task.cancel()
                del self._tasks[connection_id]

    async def aclose(self) -> None:
        tasks = tuple(self._tasks.values())
        self._tasks.clear()
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _run_connection(self, connection_id: UUID) -> None:
        delay = 2
        while True:
            stream_started: float | None = None
            key_expired = False
            try:
                exchange = await self._resolver.exchange_for(connection_id)
                if exchange.capabilities.exchange_id != "binance-usdm":
                    raise RuntimeError("USD-M bot connection resolved to a different exchange")
                await self._reconciler.resolve_pending(connection_id)
                await self._sync_protective_stops(connection_id)
                await self._recover_funding_income(connection_id, exchange)
                await self._reconcile_clean(connection_id, inspect_unowned_futures_orders=True)
                last_reconcile = 0.0
                last_account_order_scan = asyncio.get_running_loop().time()
                stream_started = asyncio.get_running_loop().time()
                async for event in exchange.stream_user_events():
                    delay = 2
                    event_type = str(event.get("e") or event.get("eventType") or "")
                    if event_type == "listenKeyExpired":
                        key_expired = True
                    if event_type in {"MARGIN_CALL", "ACCOUNT_CONFIG_UPDATE"}:
                        await self._pause_connection(
                            connection_id,
                            (
                                "risk.futures_margin_call"
                                if event_type == "MARGIN_CALL"
                                else "risk.futures_account_config_changed"
                            ),
                            event_type,
                        )
                    if event_type == "ACCOUNT_UPDATE":
                        await self._settle_funding_income(connection_id, exchange, event)
                    if event_type in {
                        "ORDER_TRADE_UPDATE",
                        "ALGO_UPDATE",
                        "CONDITIONAL_ORDER_TRIGGER_REJECT",
                    }:
                        await self._reconciler.resolve_pending(connection_id)
                        await self._sync_protective_stops(connection_id)
                    now = asyncio.get_running_loop().time()
                    if now - last_reconcile >= 1.0:
                        await self._reconciler.resolve_pending(connection_id)
                        inspect_orders = (
                            now - last_account_order_scan >= ACCOUNT_WIDE_ORDER_SCAN_SECONDS
                        )
                        await self._reconcile_clean(
                            connection_id, inspect_unowned_futures_orders=inspect_orders
                        )
                        if inspect_orders:
                            last_account_order_scan = now
                        last_reconcile = now
                raise RuntimeError("Binance USD-M private stream ended")
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                if self._is_planned_end(stream_started, key_expired):
                    # Binance closes every private socket after 24 h and expires listen keys:
                    # that is routine, not a fault. The top of this loop re-reads the account
                    # over REST (orders, stops, funding, reconciliation) before reconnecting,
                    # and the positions keep their resting native stops meanwhile.
                    logger.info(
                        "Binance USD-M private stream for connection %s ended as scheduled; "
                        "resyncing and reconnecting",
                        connection_id,
                    )
                    continue
                logger.error(
                    "Binance USD-M private stream unavailable for connection %s (%s)",
                    connection_id,
                    type(exc).__name__,
                )
                # Do not reconnect until the bots are paused and REST is authoritative again.
                while True:
                    try:
                        await self._pause_connection(
                            connection_id,
                            "risk.futures_user_stream_disconnected",
                            type(exc).__name__,
                        )
                        # A fresh account snapshot is the recovery authority after every gap.
                        recovery_exchange = await self._resolver.exchange_for(connection_id)
                        if recovery_exchange.capabilities.exchange_id != "binance-usdm":
                            raise RuntimeError(
                                "USD-M bot connection resolved to a different exchange"
                            )
                        await self._reconciler.resolve_pending(connection_id)
                        await self._sync_protective_stops(connection_id)
                        await self._recover_funding_income(connection_id, recovery_exchange)
                        await self._reconcile_clean(
                            connection_id, inspect_unowned_futures_orders=True
                        )
                        break
                    except Exception:
                        logger.exception(
                            "Futures stream recovery gate failed for connection %s; "
                            "will retry before reconnecting",
                            connection_id,
                        )
                        await asyncio.sleep(delay)
                        delay = min(delay * 2, 60)
                await asyncio.sleep(delay)
                delay = min(delay * 2, 60)

    @staticmethod
    def _is_planned_end(stream_started: float | None, key_expired: bool) -> bool:
        if key_expired:
            return True
        if stream_started is None:
            return False
        return asyncio.get_running_loop().time() - stream_started >= PLANNED_STREAM_END_SECONDS

    async def _reconcile_clean(
        self, connection_id: UUID, *, inspect_unowned_futures_orders: bool
    ) -> None:
        mismatches = await self._reconciler.reconcile_connection(
            connection_id, inspect_unowned_futures_orders=inspect_unowned_futures_orders
        )
        if mismatches:
            raise RuntimeError("Binance USD-M REST reconciliation is not clean")

    async def _sync_protective_stops(self, connection_id: UUID) -> None:
        async with self._stores() as store:
            list_connection_bots = getattr(store.bots, "list_connection_bots", None)
            account_bots = (
                await list_connection_bots(connection_id)
                if callable(list_connection_bots)
                else await store.bots.list_bots(500)
            )
            bots = [
                bot
                for bot in account_bots
                if bot.config.connection_id == connection_id
                and bot.config.product is TradingProduct.LINEAR_PERPETUAL
                and bot.config.mode.uses_exchange
                and _is_active(bot)
            ]
        for bot in bots:
            await self._executor.sync_native_stop(bot)

    async def _pause_connection(self, connection_id: UUID, event_type: str, reason: str) -> None:
        async with self._stores() as store:
            list_connection_bots = getattr(store.bots, "list_connection_bots", None)
            account_bots = (
                await list_connection_bots(connection_id)
                if callable(list_connection_bots)
                else await store.bots.list_bots(500)
            )
            bots = [
                bot
                for bot in account_bots
                if bot.config.connection_id == connection_id
                and bot.config.product is TradingProduct.LINEAR_PERPETUAL
                and bot.config.mode.uses_exchange
                and _is_active(bot)
            ]
            for bot in bots:
                await store.bots.set_desired(bot.id, BotState.PAUSED)
                await store.bots.set_observed(bot.id, BotState.PAUSED, event_type)
                await store.audit.add(
                    AuditEvent(
                        event_type,
                        "bot",
                        str(bot.id),
                        actor="worker",
                        bot_id=bot.id,
                        payload={"reason_type": reason, "at": self._clock.now().isoformat()},
                    )
                )
            await store.commit()

    async def _recover_funding_income(self, connection_id: UUID, exchange: Exchange) -> None:
        """Backfill recent settled funding after a stream gap or worker restart.

        Recovery is limited to funding events after the most recent local position change. If
        the position could have changed while events were missed, its historical isolated
        margin cannot be reconstructed from the current account snapshot, so reconciliation
        must fail closed instead of fabricating a ledger history.
        """
        async with self._stores() as store:
            list_connection_bots = getattr(store.bots, "list_connection_bots", None)
            account_bots = (
                await list_connection_bots(connection_id)
                if callable(list_connection_bots)
                else await store.bots.list_bots(500)
            )
            bots = [
                bot
                for bot in account_bots
                if bot.config.connection_id == connection_id
                and bot.config.product is TradingProduct.LINEAR_PERPETUAL
                and bot.config.mode is ExecutionMode.TESTNET
                and _is_active(bot)
            ]
        for bot in bots:
            async with self._stores() as store:
                if await store.orders.count_unresolved(bot.id):
                    continue
                ledger = await store.perpetual_portfolio.get(bot.id)
                if ledger is None or ledger.position is None:
                    continue
                entries = await store.perpetual_portfolio.list_entries(bot.id)
            local_position = ledger.position
            position_changes = [
                entry
                for entry in entries
                if entry.kind
                in {
                    PerpetualLedgerEventKind.POSITION_OPENED,
                    PerpetualLedgerEventKind.POSITION_INCREASED,
                    PerpetualLedgerEventKind.POSITION_REDUCED,
                    PerpetualLedgerEventKind.LIQUIDATED,
                }
            ]
            if not position_changes:
                raise DomainError(
                    "open Futures ledger has no position history for funding recovery"
                )
            earliest_position_change = min(entry.occurred_at for entry in position_changes)
            now = self._clock.now()
            retention_start = now - timedelta(days=89)
            # Read back to the first local position change still inside Binance's income
            # retention. Starting at the latest change would hide missing funding that occurred
            # before a later fill, making the ambiguity check below ineffective.
            since = max(earliest_position_change, retention_start)
            rows = await self._funding_income_pages(bot.config.symbol, since, now, exchange)
            known = {
                entry.external_reference.removeprefix("binance:funding:")
                for entry in entries
                if entry.kind is PerpetualLedgerEventKind.FUNDING_SETTLED
                and entry.external_reference is not None
                and entry.external_reference.startswith("binance:funding:")
            }
            missing = [
                row for row in rows if row.asset == "USDT" and row.transaction_id not in known
            ]
            if not missing:
                continue
            latest_position_change = max(entry.occurred_at for entry in position_changes)
            if any(row.occurred_at <= latest_position_change for row in missing):
                # An earlier funding payment could have affected the next recorded fill or
                # close. We cannot reconstruct its isolated-wallet allocation from today's view.
                raise DomainError("unreconciled funding predates the latest position change")

            remote_positions = await exchange.fetch_positions([bot.config.symbol])
            remote = next(
                (item for item in remote_positions if item.symbol == bot.config.symbol), None
            )
            if (
                remote is None
                or remote.side is not local_position.side
                or remote.quantity != local_position.quantity
                or remote.entry_price != local_position.entry_price
                or remote.leverage != local_position.leverage
                or remote.isolated_margin is None
            ):
                # The ordinary account reconciler records and pauses this mismatch.
                continue
            margin_delta = remote.isolated_margin - local_position.isolated_margin
            max_explainable = sum((abs(row.amount) for row in missing), Decimal(0))
            if abs(margin_delta) > max_explainable + Decimal("0.00000001"):
                raise DomainError(
                    "isolated-margin drift exceeds the missing Binance funding transactions"
                )

            missing.sort(key=lambda row: (row.occurred_at, row.transaction_id))
            async with self._stores() as store:
                ledger_service = PerpetualLedgerService(store.perpetual_portfolio)
                for index, income in enumerate(missing):
                    # Past income rows do not carry historical isolatedWallet snapshots. Apply
                    # each signed cash flow to wallet, then reclass only the aggregate difference
                    # into isolated margin on the last row using today's Binance position view.
                    margin_after = (
                        remote.isolated_margin
                        if index == len(missing) - 1
                        else local_position.isolated_margin
                    )
                    settled = await ledger_service.settle_exchange_funding_income(
                        bot.id,
                        amount=income.amount,
                        isolated_margin_after=margin_after,
                        occurred_at=income.occurred_at,
                        transaction_id=income.transaction_id,
                        source="binance_income_backfill",
                    )
                    if settled:
                        await store.audit.add(
                            AuditEvent(
                                "futures.funding_backfilled",
                                "bot",
                                str(bot.id),
                                actor="worker",
                                bot_id=bot.id,
                                payload={
                                    "symbol": bot.config.symbol,
                                    "income": str(income.amount),
                                    "transaction_id": income.transaction_id,
                                    "time": income.occurred_at.isoformat(),
                                },
                            )
                        )
                await store.commit()

    @staticmethod
    async def _funding_income_pages(
        symbol: str, start: datetime, end: datetime, exchange: Exchange
    ) -> list[FundingIncome]:
        rows_by_id: dict[str, FundingIncome] = {}
        cursor = start
        while cursor <= end:
            page = await exchange.fetch_funding_income(symbol, cursor, end, 1000)
            for row in page:
                if start <= row.occurred_at <= end:
                    rows_by_id[row.transaction_id] = row
            if len(page) < 1000:
                break
            newest = max((row.occurred_at for row in page), default=None)
            if newest is None or newest < cursor:
                raise DomainError("Binance funding history pagination moved backwards")
            next_cursor = newest + timedelta(milliseconds=1)
            if next_cursor <= cursor:
                raise DomainError("Binance funding history pagination made no progress")
            cursor = next_cursor
        return sorted(rows_by_id.values(), key=lambda row: (row.occurred_at, row.transaction_id))

    async def _settle_funding_income(
        self, connection_id: UUID, exchange: Exchange, event: dict[str, object]
    ) -> None:
        """Use Binance's actual income and post-settlement isolated wallet for funding events."""
        account = event.get("a")
        if not isinstance(account, dict) or account.get("m") != "FUNDING_FEE":
            return
        symbol = account.get("S")
        event_millis = event.get("T")
        positions = account.get("P")
        if not isinstance(symbol, str) or not symbol or not isinstance(event_millis, int):
            raise DomainError(
                "Binance funding account update is missing symbol or transaction time"
            )
        if not isinstance(positions, list):
            raise DomainError("Binance funding account update is missing position details")
        matching_positions = [
            position
            for position in positions
            if isinstance(position, dict) and position.get("s") == symbol
        ]
        if len(matching_positions) != 1:
            raise DomainError("Binance funding event did not identify one isolated position")
        position_update = matching_positions[0]
        if position_update.get("mt") != "isolated":
            raise DomainError("USD-M funding event is not for the required isolated margin mode")
        try:
            isolated_margin_after = Decimal(str(position_update["iw"]))
            occurred_at = datetime.fromtimestamp(event_millis / 1000, UTC)
        except (KeyError, InvalidOperation, TypeError, ValueError, OverflowError) as exc:
            raise DomainError("Binance funding event has malformed margin or timestamp") from exc
        if not isolated_margin_after.is_finite() or isolated_margin_after <= 0:
            raise DomainError("Binance funding event reports invalid isolated position margin")

        async with self._stores() as store:
            list_connection_bots = getattr(store.bots, "list_connection_bots", None)
            account_bots = (
                await list_connection_bots(connection_id)
                if callable(list_connection_bots)
                else await store.bots.list_bots(500)
            )
            bots = [
                bot
                for bot in account_bots
                if bot.config.connection_id == connection_id
                and bot.config.product is TradingProduct.LINEAR_PERPETUAL
                and bot.config.mode is ExecutionMode.TESTNET
                and _is_active(bot)
                and bot.config.symbol.partition(":")[0].replace("/", "") == symbol
            ]
        if not bots:
            return  # funding on an unrelated manually managed symbol is not this worker's ledger
        if len(bots) != 1:
            raise DomainError("more than one Futures bot owns the funding event symbol")
        bot = bots[0]
        income_start = occurred_at - timedelta(seconds=60)
        income_end = occurred_at + timedelta(seconds=60)
        income_rows = await exchange.fetch_funding_income(
            bot.config.symbol, income_start, income_end, 1000
        )
        nearest = sorted(
            (row for row in income_rows if row.asset == "USDT"),
            key=lambda row: abs((row.occurred_at - occurred_at).total_seconds()),
        )
        if not nearest or abs((nearest[0].occurred_at - occurred_at).total_seconds()) > 5:
            raise DomainError("matching Binance FUNDING_FEE income row is not available yet")
        if len(nearest) > 1 and nearest[0].occurred_at == nearest[1].occurred_at:
            raise DomainError("Binance returned ambiguous funding transactions for this event")
        income = nearest[0]
        async with self._stores() as store:
            ledger_service = PerpetualLedgerService(store.perpetual_portfolio)
            settled = await ledger_service.settle_exchange_funding_income(
                bot.id,
                amount=income.amount,
                isolated_margin_after=isolated_margin_after,
                occurred_at=income.occurred_at,
                transaction_id=income.transaction_id,
            )
            if settled:
                await store.audit.add(
                    AuditEvent(
                        "futures.funding_settled",
                        "bot",
                        str(bot.id),
                        actor="worker",
                        bot_id=bot.id,
                        payload={
                            "symbol": bot.config.symbol,
                            "income": str(income.amount),
                            "asset": income.asset,
                            "transaction_id": income.transaction_id,
                            "time": income.occurred_at.isoformat(),
                        },
                    )
                )
            await store.commit()
