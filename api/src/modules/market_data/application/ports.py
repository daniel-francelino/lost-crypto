from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from core.jobs import JobStatus
from modules.market_data.domain.models import (
    Candle,
    ListedMarket,
    Listing,
    MarketInfo,
    RegimeBreak,
    Timeframe,
)


class MarketDataSource(Protocol):
    """Where market data comes from (an exchange adapter, or a fake in tests)."""

    async def fetch_candles(
        self, symbol: str, timeframe: Timeframe, since: datetime, limit: int
    ) -> list[Candle]:
        """Candles with ``open_time >= since``, ascending. May include the in-progress one."""
        ...

    async def fetch_market_info(self, symbol: str) -> MarketInfo: ...


class CandleRepository(Protocol):
    async def upsert_many(self, exchange: str, candles: Sequence[Candle]) -> int: ...

    async def get_range(
        self, exchange: str, symbol: str, timeframe: Timeframe, start: datetime, end: datetime
    ) -> list[Candle]:
        """Candles with ``start <= open_time < end``, ascending."""
        ...

    async def count_range(
        self, exchange: str, symbol: str, timeframe: Timeframe, start: datetime, end: datetime
    ) -> int: ...

    async def bounds(
        self, exchange: str, symbol: str, timeframe: Timeframe
    ) -> tuple[int, datetime | None, datetime | None]:
        """(count, first open_time, last open_time) of the stored series."""
        ...

    async def last_open_time(
        self, exchange: str, symbol: str, timeframe: Timeframe
    ) -> datetime | None: ...

    async def list_series(self, last_after: datetime) -> list[tuple[str, str, Timeframe, datetime]]:
        """(exchange, symbol, timeframe, last open_time) of every stored series whose last
        candle opened at or after ``last_after``."""
        ...

    async def open_times(
        self, exchange: str, symbol: str, timeframe: Timeframe, start: datetime, end: datetime
    ) -> list[datetime]: ...


class RegimeBreakRepository(Protocol):
    async def add(self, regime_break: RegimeBreak) -> bool:
        """False when a break with the same name and date already exists."""
        ...

    async def list_breaks(self, exchange: str | None, symbol: str | None) -> list[RegimeBreak]:
        """Breaks that apply to the market (global ones included); all when no filter."""
        ...

    async def delete(self, break_id: UUID) -> bool: ...

    async def inside(
        self, exchange: str, symbol: str, start: datetime, end: datetime
    ) -> list[RegimeBreak]:
        """Breaks of this market (or global) with ``start < occurred_at <= end``."""
        ...


class ListingRepository(Protocol):
    """Point-in-time listings per exchange (see ``application.listings``)."""

    async def record(self, exchange: str, markets: list[ListedMarket], now: datetime) -> int: ...
    async def list(self, exchange: str, symbol: str | None = None) -> list[Listing]: ...


@dataclass(slots=True)
class ImportJob:
    id: UUID
    exchange: str
    symbol: str
    timeframe: Timeframe
    start: datetime
    end: datetime
    status: JobStatus
    candles_imported: int
    error: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    # Data quality (book 1 ch. 3, O3): invalid candles are not stored; changed ones are counted.
    candles_rejected: int = 0
    candles_changed: int = 0
    rejection_samples: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ImportQuality:
    rejected: int = 0
    changed: int = 0
    samples: tuple[dict[str, Any], ...] = ()


NO_ISSUES = ImportQuality()


class ImportStore(Protocol):
    """One transaction scope for import jobs and candles."""

    @property
    def candles(self) -> CandleRepository: ...

    @property
    def listings(self) -> ListingRepository: ...

    @property
    def regime_breaks(self) -> RegimeBreakRepository: ...

    async def add_job(self, job: ImportJob) -> None: ...
    async def get_job(self, job_id: UUID) -> ImportJob | None: ...
    async def list_jobs(self, limit: int) -> list[ImportJob]: ...
    async def claim_next_queued(self) -> ImportJob | None: ...
    async def requeue_running(self) -> int: ...
    async def set_progress(
        self, job_id: UUID, candles_imported: int, quality: ImportQuality = NO_ISSUES
    ) -> None: ...
    async def mark_completed(
        self, job_id: UUID, candles_imported: int, quality: ImportQuality = NO_ISSUES
    ) -> None: ...
    async def mark_failed(self, job_id: UUID, error: str) -> None: ...
    async def commit(self) -> None: ...
