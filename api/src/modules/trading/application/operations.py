"""Operational checks the worker runs on its own schedule (book 1 ch. 4).

Clock skew: the trader decides "this candle has closed" by the local clock and Binance refuses
signed requests outside its time window, so the difference with the exchange's clock is
measured regularly and stored for the status screen and the trader's live-entry guard.
"""

import logging
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from core.clock import Clock
from modules.trading.application.ports import TradingStore

if TYPE_CHECKING:
    from modules.exchanges.application.registry import ExchangeRegistry

logger = logging.getLogger(__name__)

MEASURE_EVERY = timedelta(minutes=1)


@runtime_checkable
class ServerClock(Protocol):
    async def fetch_server_time(self) -> datetime: ...


def skew_ms(sent: datetime, received: datetime, server: datetime) -> int:
    """Local minus exchange time, taking the local midpoint of the round trip."""
    local = sent + (received - sent) / 2
    return int((local - server).total_seconds() * 1000)


class OperationsMonitor:
    def __init__(
        self,
        stores: Callable[[], AbstractAsyncContextManager[TradingStore]],
        exchanges: "ExchangeRegistry",
        clock: Clock,
        every: timedelta = MEASURE_EVERY,
    ) -> None:
        self._stores = stores
        self._exchanges = exchanges
        self._clock = clock
        self._every = every
        self._next: datetime | None = None

    async def run_due(self) -> bool:
        now = self._clock.now()
        if self._next is not None and now < self._next:
            return False
        self._next = now + self._every
        worst: int | None = None
        for exchange_id in self._exchanges.exchange_ids():
            source = self._exchanges.market_data(exchange_id)
            if not isinstance(source, ServerClock):
                continue
            try:
                sent = self._clock.now()
                server = await source.fetch_server_time()
                measured = skew_ms(sent, self._clock.now(), server)
            except Exception:
                logger.warning("clock check against %s failed", exchange_id, exc_info=True)
                continue
            if worst is None or abs(measured) > abs(worst):
                worst = measured
        if worst is None:
            return False
        async with self._stores() as store:
            await store.flags.set_clock_skew(worst, self._clock.now())
            await store.commit()
        if abs(worst) > 1000:
            logger.warning("server clock is %d ms off the exchange: sync it (NTP)", worst)
        return True
