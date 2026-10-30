from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from core.jobs import JobStatus
from modules.market_data.domain.models import Candle, MarketInfo, Timeframe


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

    async def open_times(
        self, exchange: str, symbol: str, timeframe: Timeframe, start: datetime, end: datetime
    ) -> list[datetime]: ...


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


class ImportStore(Protocol):
    """One transaction scope for import jobs and candles."""

    @property
    def candles(self) -> CandleRepository: ...

    async def add_job(self, job: ImportJob) -> None: ...
    async def get_job(self, job_id: UUID) -> ImportJob | None: ...
    async def list_jobs(self, limit: int) -> list[ImportJob]: ...
    async def claim_next_queued(self) -> ImportJob | None: ...
    async def requeue_running(self) -> int: ...
    async def set_progress(self, job_id: UUID, candles_imported: int) -> None: ...
    async def mark_completed(self, job_id: UUID, candles_imported: int) -> None: ...
    async def mark_failed(self, job_id: UUID, error: str) -> None: ...
    async def commit(self) -> None: ...
