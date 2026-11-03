import asyncio
import logging
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from core.clock import Clock
from core.errors import ConflictError, DomainError, NotFoundError
from core.ids import IdGenerator
from core.jobs import JobStatus
from modules.analytics.domain import mean_reversion
from modules.analytics.domain.mean_reversion import HalfLife, VarianceRatio
from modules.analytics.domain.momentum import GridCell, lagged_return_grid
from modules.exchanges.application.registry import ExchangeRegistry
from modules.market_data.application.ports import ImportJob, ImportQuality, ImportStore
from modules.market_data.domain.models import (
    Candle,
    FundingRate,
    Gap,
    Listing,
    RangeCoverage,
    RegimeBreak,
    Timeframe,
    find_gaps,
    floor_to_timeframe,
    range_coverage,
)
from modules.market_data.domain.quality import (
    DEFAULT_OUTLIER_SIGMAS,
    Outlier,
    candle_problems,
    find_outliers,
    returns_by_time,
)

logger = logging.getLogger(__name__)

ImportStoreFactory = Callable[[], AbstractAsyncContextManager[ImportStore]]

BATCH_SIZE = 1000
MAX_REJECTION_SAMPLES = 20
REFERENCE_SYMBOL = "BTC/USDT"  # "did the whole market move?" (our adaptation of Chan p. 43)
MAX_OUTLIER_CANDLES = 200_000
MAX_ANALYSIS_CANDLES = 200_000


class InvalidImportRequest(DomainError):
    pass


class RegimeBreakNotFound(NotFoundError):
    pass


@dataclass(frozen=True, slots=True)
class Coverage:
    exchange: str
    symbol: str
    timeframe: Timeframe
    count: int
    first: datetime | None
    last: datetime | None
    gaps: list[Gap]
    in_range: RangeCoverage | None = None  # when a start/end was asked for


@dataclass(frozen=True, slots=True)
class SeriesDiagnostics:
    half_life: HalfLife | None
    hurst: Decimal | None
    variance_ratios: list[VarianceRatio]


def _diagnose(closes: list[Decimal], log: bool) -> SeriesDiagnostics:
    ratios = [
        r
        for lag in mean_reversion.VARIANCE_RATIO_LAGS
        if (r := mean_reversion.variance_ratio(closes, lag, log=log)) is not None
    ]
    return SeriesDiagnostics(
        mean_reversion.half_life(closes, log=log), mean_reversion.hurst(closes, log=log), ratios
    )


class MarketDataService:
    """API-side use cases: queue imports, query stored candles and coverage."""

    def __init__(
        self,
        stores: ImportStoreFactory,
        exchanges: ExchangeRegistry,
        clock: Clock,
        ids: IdGenerator,
    ) -> None:
        self._stores = stores
        self._exchanges = exchanges
        self._clock = clock
        self._ids = ids

    async def request_import(
        self, exchange: str, symbol: str, timeframe: Timeframe, start: datetime, end: datetime
    ) -> ImportJob:
        if start >= end:
            raise InvalidImportRequest("start must be before end")
        self._exchanges.require(exchange, timeframe)
        job = ImportJob(
            id=self._ids.new_id(),
            exchange=exchange,
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

    async def import_perpetual_auxiliary(
        self,
        exchange: str,
        symbol: str,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
    ) -> tuple[int, int]:
        """Fetch exact historical mark candles and funding events into their separate stores."""
        from modules.exchanges.domain.models import TradingProduct

        if start >= end:
            raise InvalidImportRequest("start must be before end")
        profile = self._exchanges.require(exchange, timeframe)
        if TradingProduct.LINEAR_PERPETUAL not in profile.capabilities.products:
            raise InvalidImportRequest(f"{exchange} does not provide perpetual market data")
        source = self._exchanges.exchange(exchange)
        fetch_mark_candles = getattr(source, "fetch_mark_candles", None)
        fetch_funding_rates = getattr(source, "fetch_funding_rates", None)
        if not callable(fetch_mark_candles) or not callable(fetch_funding_rates):
            raise InvalidImportRequest(f"{exchange} has no mark-price or funding history source")

        marks: list[Candle] = []
        cursor = floor_to_timeframe(start, timeframe)
        while cursor < end:
            page = await fetch_mark_candles(symbol, timeframe, cursor, 1000)
            page = sorted(
                (c for c in page if start <= c.open_time < end), key=lambda c: c.open_time
            )
            if not page:
                break
            marks.extend(page)
            next_cursor = page[-1].open_time + timeframe.delta
            if next_cursor <= cursor:
                raise InvalidImportRequest("mark-price history pagination did not advance")
            cursor = next_cursor

        rates: list[FundingRate] = []
        funding_cursor = start
        while funding_cursor < end:
            page = await fetch_funding_rates(symbol, funding_cursor, 1000)
            page = sorted(
                (r for r in page if start <= r.funding_time <= end),
                key=lambda r: r.funding_time,
            )
            if not page:
                break
            rates.extend(page)
            next_cursor = page[-1].funding_time + timedelta(milliseconds=1)
            if next_cursor <= funding_cursor:
                raise InvalidImportRequest("funding history pagination did not advance")
            funding_cursor = next_cursor

        if not marks:
            raise InvalidImportRequest("exchange returned no mark-price candles for this range")
        async with self._stores() as store:
            await store.perpetual_data.upsert_mark_candles(exchange, marks)
            await store.perpetual_data.upsert_funding_rates(exchange, rates)
            await store.commit()
        return len(marks), len(rates)

    async def get_import(self, job_id: UUID) -> ImportJob | None:
        async with self._stores() as store:
            return await store.get_job(job_id)

    async def list_imports(self, limit: int = 50) -> list[ImportJob]:
        async with self._stores() as store:
            return await store.list_jobs(limit)

    async def candles(
        self, exchange: str, symbol: str, timeframe: Timeframe, start: datetime, end: datetime
    ) -> list[Candle]:
        self._exchanges.profile(exchange)
        async with self._stores() as store:
            return await store.candles.get_range(exchange, symbol, timeframe, start, end)

    async def coverage(
        self,
        exchange: str,
        symbol: str,
        timeframe: Timeframe,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Coverage:
        self._exchanges.profile(exchange)
        async with self._stores() as store:
            count, first, last = await store.candles.bounds(exchange, symbol, timeframe)
            gaps: list[Gap] = []
            times: list[datetime] = []
            if first is not None and last is not None:
                times = await store.candles.open_times(
                    exchange, symbol, timeframe, first, last + timeframe.delta
                )
                gaps = find_gaps(times, timeframe)
        in_range = None
        if start is not None and end is not None:
            in_range = range_coverage(times, timeframe, start, end, self._clock.now())
        return Coverage(exchange, symbol, timeframe, count, first, last, gaps, in_range)

    async def listings(self, exchange: str, symbol: str | None = None) -> list[Listing]:
        self._exchanges.profile(exchange)
        async with self._stores() as store:
            return await store.listings.list(exchange, symbol)

    async def outliers(
        self,
        exchange: str,
        symbol: str,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
        k: Decimal = DEFAULT_OUTLIER_SIGMAS,
    ) -> list[Outlier]:
        """Returns beyond ``k`` sigmas in the range, each with the reference pair's move."""
        self._exchanges.profile(exchange)
        async with self._stores() as store:
            if await store.candles.count_range(exchange, symbol, timeframe, start, end) > (
                MAX_OUTLIER_CANDLES
            ):
                raise InvalidImportRequest(f"at most {MAX_OUTLIER_CANDLES} candles per request")
            candles = await store.candles.get_range(exchange, symbol, timeframe, start, end)
            reference: list[Candle] = []
            if symbol != REFERENCE_SYMBOL:
                reference = await store.candles.get_range(
                    exchange, REFERENCE_SYMBOL, timeframe, start, end
                )
        return find_outliers(candles, k, returns_by_time(reference) if reference else None)

    async def half_life(
        self,
        exchange: str,
        symbol: str,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
        *,
        log: bool = True,
        sample_every: int = 1,
    ) -> tuple[SeriesDiagnostics, int, int]:
        self._exchanges.profile(exchange)
        async with self._stores() as store:
            count = await store.candles.count_range(exchange, symbol, timeframe, start, end)
            if count > MAX_ANALYSIS_CANDLES:
                raise InvalidImportRequest(
                    f"at most {MAX_ANALYSIS_CANDLES} candles per half-life request"
                )
            candles = await store.candles.get_range(exchange, symbol, timeframe, start, end)
        closes = mean_reversion.sample_every([c.close for c in candles], sample_every)
        diagnostics = await asyncio.to_thread(_diagnose, closes, log)
        return diagnostics, len(closes), len(find_gaps([c.open_time for c in candles], timeframe))

    async def create_break(
        self,
        name: str,
        occurred_at: datetime,
        exchange: str | None,
        symbol: str | None,
        note: str | None,
        actor: str,
    ) -> RegimeBreak:
        """Register a named break. It is never edited: to fix one, delete it and create again,
        which leaves a trail (the point is to name breaks before looking at results)."""
        if exchange is not None:
            self._exchanges.profile(exchange)
        regime_break = RegimeBreak(
            self._ids.new_id(), name, occurred_at, exchange, symbol, note, actor, self._clock.now()
        )
        async with self._stores() as store:
            if not await store.regime_breaks.add(regime_break):
                raise ConflictError(f"a break named {name!r} on that date already exists")
            await store.commit()
        return regime_break

    async def list_breaks(self, exchange: str | None, symbol: str | None) -> list[RegimeBreak]:
        async with self._stores() as store:
            return await store.regime_breaks.list_breaks(exchange, symbol)

    async def delete_break(self, break_id: UUID) -> None:
        async with self._stores() as store:
            if not await store.regime_breaks.delete(break_id):
                raise RegimeBreakNotFound(f"break {break_id} not found")
            await store.commit()

    async def momentum_grid(
        self,
        exchange: str,
        symbol: str,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
        lookbacks: list[int],
        holdings: list[int],
    ) -> tuple[list[GridCell], Decimal, Decimal, int, int]:
        """The lagged-return correlation grid over stored closes: the cells, the corrected level,
        its critical z, the number of candles and the number of gaps."""
        self._exchanges.profile(exchange)
        async with self._stores() as store:
            count = await store.candles.count_range(exchange, symbol, timeframe, start, end)
            if count > MAX_ANALYSIS_CANDLES:
                raise InvalidImportRequest(
                    f"at most {MAX_ANALYSIS_CANDLES} candles per momentum-grid request"
                )
            candles = await store.candles.get_range(exchange, symbol, timeframe, start, end)
        try:
            cells, alpha, critical = await asyncio.to_thread(
                lagged_return_grid, [c.close for c in candles], lookbacks, holdings
            )
        except ValueError as exc:
            raise InvalidImportRequest(str(exc)) from exc
        gaps = len(find_gaps([c.open_time for c in candles], timeframe))
        return cells, alpha, critical, len(candles), gaps


class CandleImporter:
    """Worker-side: executes queued import jobs. Idempotent (candles are upserted), so a
    job interrupted by a crash can simply run again."""

    def __init__(
        self, stores: ImportStoreFactory, exchanges: ExchangeRegistry, clock: Clock
    ) -> None:
        self._stores = stores
        self._exchanges = exchanges
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
            total, quality = await self._import(job)
        except Exception as exc:
            logger.exception("import job %s failed", job.id)
            async with self._stores() as store:
                await store.mark_failed(job.id, f"{type(exc).__name__}: {exc}"[:500])
                await store.commit()
        else:
            async with self._stores() as store:
                await store.mark_completed(job.id, total, quality)
                await store.commit()
            logger.info(
                "import job %s completed: %d candles, %d rejected, %d changed",
                job.id,
                total,
                quality.rejected,
                quality.changed,
            )
        return True

    async def _import(self, job: ImportJob) -> tuple[int, ImportQuality]:
        timeframe = job.timeframe
        source = self._exchanges.market_data(job.exchange)
        cursor = floor_to_timeframe(job.start, timeframe)
        # Only closed candles: the one containing "now" is still in progress.
        end = min(job.end, floor_to_timeframe(self._clock.now(), timeframe))
        total = 0
        quality = ImportQuality()
        while cursor < end:
            batch = await source.fetch_candles(job.symbol, timeframe, cursor, BATCH_SIZE)
            batch = [c for c in batch if cursor <= c.open_time < end]
            if not batch:
                break
            valid, rejected = _split_valid(batch)
            async with self._stores() as store:
                changed = await _count_changed(store, job, valid)
                quality = _merge(quality, rejected, changed)
                total += await store.candles.upsert_many(job.exchange, valid) if valid else 0
                await store.set_progress(job.id, total, quality)
                await store.commit()
            next_cursor = max(c.open_time for c in batch) + timeframe.delta
            if next_cursor <= cursor:
                break
            cursor = next_cursor
        return total, quality


def _split_valid(batch: list[Candle]) -> tuple[list[Candle], list[dict[str, Any]]]:
    """Candles that can be stored, and a sample row for each one that cannot."""
    valid: list[Candle] = []
    rejected: list[dict[str, Any]] = []
    for candle in batch:
        problems = candle_problems(candle)
        if problems:
            rejected.append(
                {"open_time": candle.open_time.isoformat(), "problems": [p.value for p in problems]}
            )
        else:
            valid.append(candle)
    return valid, rejected


async def _count_changed(store: ImportStore, job: ImportJob, batch: list[Candle]) -> int:
    """Stored candles whose OHLCV the exchange now reports differently (they get overwritten)."""
    if not batch:
        return 0
    first, last = batch[0].open_time, batch[-1].open_time + job.timeframe.delta
    stored = {
        c.open_time: c
        for c in await store.candles.get_range(job.exchange, job.symbol, job.timeframe, first, last)
    }
    return sum(
        1
        for c in batch
        if (old := stored.get(c.open_time)) is not None
        and (old.open, old.high, old.low, old.close, old.volume)
        != (c.open, c.high, c.low, c.close, c.volume)
    )


def _merge(quality: ImportQuality, rejected: list[dict[str, Any]], changed: int) -> ImportQuality:
    room = MAX_REJECTION_SAMPLES - len(quality.samples)
    return ImportQuality(
        rejected=quality.rejected + len(rejected),
        changed=quality.changed + changed,
        samples=(*quality.samples, *rejected[: max(room, 0)]),
    )
