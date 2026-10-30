import logging
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from core.clock import Clock
from core.errors import DomainError
from core.ids import IdGenerator
from core.jobs import JobStatus
from modules.market_data.application.ports import (
    ImportJob,
    ImportStore,
    MarketDataSource,
)
from modules.market_data.domain.models import (
    Candle,
    Gap,
    Timeframe,
    find_gaps,
    floor_to_timeframe,
)

logger = logging.getLogger(__name__)

ImportStoreFactory = Callable[[], AbstractAsyncContextManager[ImportStore]]

BATCH_SIZE = 1000


class InvalidImportRequest(DomainError):
    pass


@dataclass(frozen=True, slots=True)
class Coverage:
    symbol: str
    timeframe: Timeframe
    count: int
    first: datetime | None
    last: datetime | None
    gaps: list[Gap]


class MarketDataService:
    """API-side use cases: queue imports, query stored candles and coverage."""

    def __init__(
        self, stores: ImportStoreFactory, exchange: str, clock: Clock, ids: IdGenerator
    ) -> None:
        self._stores = stores
        self._exchange = exchange
        self._clock = clock
        self._ids = ids

    async def request_import(
        self, symbol: str, timeframe: Timeframe, start: datetime, end: datetime
    ) -> ImportJob:
        if start >= end:
            raise InvalidImportRequest("start must be before end")
        job = ImportJob(
            id=self._ids.new_id(),
            exchange=self._exchange,
            symbol=symbol,
            timeframe=timeframe,
            start=start,
            end=end,
            status=JobStatus.QUEUED,
            candles_imported=0,
            error=None,
            created_at=self._clock.now(),
            started_at=None,
            finished_at=None,
        )
        async with self._stores() as store:
            await store.add_job(job)
            await store.commit()
        return job

    async def get_import(self, job_id: UUID) -> ImportJob | None:
        async with self._stores() as store:
            return await store.get_job(job_id)

    async def list_imports(self, limit: int = 50) -> list[ImportJob]:
        async with self._stores() as store:
            return await store.list_jobs(limit)

    async def candles(
        self, symbol: str, timeframe: Timeframe, start: datetime, end: datetime
    ) -> list[Candle]:
        async with self._stores() as store:
            return await store.candles.get_range(self._exchange, symbol, timeframe, start, end)

    async def coverage(self, symbol: str, timeframe: Timeframe) -> Coverage:
        async with self._stores() as store:
            count, first, last = await store.candles.bounds(self._exchange, symbol, timeframe)
            gaps: list[Gap] = []
            if first is not None and last is not None:
                times = await store.candles.open_times(
                    self._exchange, symbol, timeframe, first, last + timeframe.delta
                )
                gaps = find_gaps(times, timeframe)
        return Coverage(symbol, timeframe, count, first, last, gaps)


class CandleImporter:
    """Worker-side: executes queued import jobs. Idempotent (candles are upserted), so a
    job interrupted by a crash can simply run again."""

    def __init__(
        self, stores: ImportStoreFactory, source: MarketDataSource, exchange: str, clock: Clock
    ) -> None:
        self._stores = stores
        self._source = source
        self._exchange = exchange
        self._clock = clock

    async def recover(self) -> int:
        async with self._stores() as store:
            count = await store.requeue_running()
            await store.commit()
        return count

    async def run_next(self) -> bool:
        async with self._stores() as store:
            job = await store.claim_next_queued()
            await store.commit()
        if job is None:
            return False
        logger.info("import job %s started: %s %s", job.id, job.symbol, job.timeframe)
        try:
            total = await self._import(job)
        except Exception as exc:
            logger.exception("import job %s failed", job.id)
            async with self._stores() as store:
                await store.mark_failed(job.id, f"{type(exc).__name__}: {exc}"[:500])
                await store.commit()
        else:
            async with self._stores() as store:
                await store.mark_completed(job.id, total)
                await store.commit()
            logger.info("import job %s completed: %d candles", job.id, total)
        return True

    async def _import(self, job: ImportJob) -> int:
        timeframe = job.timeframe
        cursor = floor_to_timeframe(job.start, timeframe)
        # Only closed candles: the one containing "now" is still in progress.
        end = min(job.end, floor_to_timeframe(self._clock.now(), timeframe))
        total = 0
        while cursor < end:
            batch = await self._source.fetch_candles(job.symbol, timeframe, cursor, BATCH_SIZE)
            batch = [c for c in batch if cursor <= c.open_time < end]
            if not batch:
                break
            async with self._stores() as store:
                total += await store.candles.upsert_many(self._exchange, batch)
                await store.set_progress(job.id, total)
                await store.commit()
            next_cursor = max(c.open_time for c in batch) + timeframe.delta
            if next_cursor <= cursor:
                break
            cursor = next_cursor
        return total
