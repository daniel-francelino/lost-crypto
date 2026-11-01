"""Point-in-time record of the pairs each exchange lists (book 1 ch. 3, C3 survivorship).

Exchanges only tell what is listed *today*. Recording it every day builds, from now on, the
history a survivorship-free universe needs: when a pair first appeared, when it was last seen,
and when it disappeared.
"""

import logging
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from core.clock import Clock
from modules.market_data.application.ports import ListingRepository
from modules.market_data.domain.models import ListedMarket

if TYPE_CHECKING:
    from modules.exchanges.application.registry import ExchangeRegistry

logger = logging.getLogger(__name__)

RECORD_EVERY = timedelta(days=1)
RETRY_AFTER = timedelta(hours=1)


@runtime_checkable
class ListingSource(Protocol):
    async def list_markets(self) -> list[ListedMarket]: ...


class ListingStore(Protocol):
    @property
    def listings(self) -> ListingRepository: ...

    async def commit(self) -> None: ...


ListingStoreFactory = Callable[[], AbstractAsyncContextManager[ListingStore]]


class ListingRecorder:
    """Worker-side: once a day, store what each exchange lists."""

    def __init__(
        self,
        stores: ListingStoreFactory,
        exchanges: "ExchangeRegistry",
        clock: Clock,
        every: timedelta = RECORD_EVERY,
    ) -> None:
        self._stores = stores
        self._exchanges = exchanges
        self._clock = clock
        self._every = every
        self._next_run: datetime | None = None

    async def run_due(self) -> bool:
        now = self._clock.now()
        if self._next_run is not None and now < self._next_run:
            return False
        self._next_run = now + self._every
        for exchange in self._exchanges.exchange_ids():
            try:
                await self._record(exchange, now)
            except Exception:
                logger.exception("listing snapshot of %s failed", exchange)
                self._next_run = now + RETRY_AFTER
        return True

    async def _record(self, exchange: str, now: datetime) -> None:
        source = self._exchanges.market_data(exchange)
        if not isinstance(source, ListingSource):
            return
        markets = await source.list_markets()
        if not markets:  # an empty answer is a failure, not "everything was delisted"
            logger.warning("listing snapshot of %s returned no markets; skipped", exchange)
            return
        async with self._stores() as store:
            changed = await store.listings.record(exchange, markets, now)
            await store.commit()
        logger.info(
            "listing snapshot of %s: %d markets, %d changed", exchange, len(markets), changed
        )
