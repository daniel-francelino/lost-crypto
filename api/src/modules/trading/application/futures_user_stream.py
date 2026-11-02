"""Private Binance USD-M Demo stream lifecycle and fail-closed reconciliation."""

import asyncio
import logging
from uuid import UUID

from core.clock import Clock
from modules.audit.models import AuditEvent
from modules.bots.domain.models import BotState, ExecutionMode
from modules.exchanges.application.connections import ConnectionResolver
from modules.exchanges.domain.models import TradingProduct
from modules.trading.application.reconciler import Reconciler
from modules.trading.application.trader import TradingStoreFactory

logger = logging.getLogger(__name__)


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
        clock: Clock,
    ) -> None:
        self._stores = stores
        self._resolver = resolver
        self._reconciler = reconciler
        self._clock = clock
        self._tasks: dict[UUID, asyncio.Task[None]] = {}

    async def ensure_running(self) -> None:
        async with self._stores() as store:
            bots = await store.bots.list_bots(500)
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
            try:
                exchange = await self._resolver.exchange_for(connection_id)
                if exchange.capabilities.exchange_id != "binance-usdm":
                    raise RuntimeError("USD-M bot connection resolved to a different exchange")
                await self._reconciler.resolve_pending(connection_id)
                await self._reconciler.reconcile_connection(connection_id)
                last_reconcile = 0.0
                async for event in exchange.stream_user_events():
                    delay = 2
                    event_type = str(event.get("e") or event.get("eventType") or "")
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
                    now = asyncio.get_running_loop().time()
                    if now - last_reconcile >= 1.0:
                        await self._reconciler.resolve_pending(connection_id)
                        await self._reconciler.reconcile_connection(connection_id)
                        last_reconcile = now
                raise RuntimeError("Binance USD-M private stream ended")
            except asyncio.CancelledError:
                raise
            except Exception as exc:
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
                        await self._reconciler.resolve_pending(connection_id)
                        await self._reconciler.reconcile_connection(connection_id)
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

    async def _pause_connection(
        self, connection_id: UUID, event_type: str, reason: str
    ) -> None:
        async with self._stores() as store:
            bots = [
                bot
                for bot in await store.bots.list_bots(500)
                if bot.config.connection_id == connection_id
                and bot.config.product is TradingProduct.LINEAR_PERPETUAL
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
