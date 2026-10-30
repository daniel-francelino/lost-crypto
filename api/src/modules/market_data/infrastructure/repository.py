from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from core.jobs import JobStatus
from modules.market_data.application.ports import ImportJob
from modules.market_data.domain.models import Candle, Timeframe
from modules.market_data.infrastructure.orm import CandleImportJobRow, CandleRow

_UPSERT_CHUNK = 1000  # 1000 rows x 9 params stays below asyncpg's 32767 bind-parameter limit


class SqlAlchemyCandleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_many(self, exchange: str, candles: Sequence[Candle]) -> int:
        for i in range(0, len(candles), _UPSERT_CHUNK):
            rows = [
                {
                    "exchange": exchange,
                    "symbol": c.symbol,
                    "timeframe": c.timeframe.value,
                    "open_time": c.open_time,
                    "open": c.open,
                    "high": c.high,
                    "low": c.low,
                    "close": c.close,
                    "volume": c.volume,
                }
                for c in candles[i : i + _UPSERT_CHUNK]
            ]
            stmt = insert(CandleRow).values(rows)
            stmt = stmt.on_conflict_do_update(
                index_elements=["exchange", "symbol", "timeframe", "open_time"],
                set_={k: stmt.excluded[k] for k in ("open", "high", "low", "close", "volume")},
            )
            await self._session.execute(stmt)
        return len(candles)

    async def get_range(
        self, exchange: str, symbol: str, timeframe: Timeframe, start: datetime, end: datetime
    ) -> list[Candle]:
        result = await self._session.execute(
            select(CandleRow)
            .where(*self._series(exchange, symbol, timeframe))
            .where(CandleRow.open_time >= start, CandleRow.open_time < end)
            .order_by(CandleRow.open_time)
        )
        return [
            Candle(
                symbol=r.symbol,
                timeframe=Timeframe(r.timeframe),
                open_time=r.open_time,
                open=r.open,
                high=r.high,
                low=r.low,
                close=r.close,
                volume=r.volume,
            )
            for r in result.scalars()
        ]

    async def count_range(
        self, exchange: str, symbol: str, timeframe: Timeframe, start: datetime, end: datetime
    ) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(CandleRow)
            .where(*self._series(exchange, symbol, timeframe))
            .where(CandleRow.open_time >= start, CandleRow.open_time < end)
        )
        return int(result.scalar_one())

    async def bounds(
        self, exchange: str, symbol: str, timeframe: Timeframe
    ) -> tuple[int, datetime | None, datetime | None]:
        result = await self._session.execute(
            select(func.count(), func.min(CandleRow.open_time), func.max(CandleRow.open_time))
            .select_from(CandleRow)
            .where(*self._series(exchange, symbol, timeframe))
        )
        count, first, last = result.one()
        return int(count), first, last

    async def open_times(
        self, exchange: str, symbol: str, timeframe: Timeframe, start: datetime, end: datetime
    ) -> list[datetime]:
        result = await self._session.execute(
            select(CandleRow.open_time)
            .where(*self._series(exchange, symbol, timeframe))
            .where(CandleRow.open_time >= start, CandleRow.open_time < end)
            .order_by(CandleRow.open_time)
        )
        return list(result.scalars())

    @staticmethod
    def _series(
        exchange: str, symbol: str, timeframe: Timeframe
    ) -> tuple[ColumnElement[bool], ...]:
        return (
            CandleRow.exchange == exchange,
            CandleRow.symbol == symbol,
            CandleRow.timeframe == timeframe.value,
        )


def _to_job(row: CandleImportJobRow) -> ImportJob:
    return ImportJob(
        id=row.id,
        exchange=row.exchange,
        symbol=row.symbol,
        timeframe=Timeframe(row.timeframe),
        start=row.start_at,
        end=row.end_at,
        status=JobStatus(row.status),
        candles_imported=row.candles_imported,
        error=row.error,
        created_at=row.created_at,
        started_at=row.started_at,
        finished_at=row.finished_at,
    )


class SqlAlchemyImportStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.candles = SqlAlchemyCandleRepository(session)

    async def add_job(self, job: ImportJob) -> None:
        self._session.add(
            CandleImportJobRow(
                id=job.id,
                exchange=job.exchange,
                symbol=job.symbol,
                timeframe=job.timeframe.value,
                start_at=job.start,
                end_at=job.end,
                status=job.status.value,
                candles_imported=job.candles_imported,
                error=job.error,
                created_at=job.created_at,
            )
        )
        await self._session.flush()

    async def get_job(self, job_id: UUID) -> ImportJob | None:
        row = await self._session.get(CandleImportJobRow, job_id)
        return _to_job(row) if row else None

    async def list_jobs(self, limit: int) -> list[ImportJob]:
        result = await self._session.execute(
            select(CandleImportJobRow).order_by(CandleImportJobRow.created_at.desc()).limit(limit)
        )
        return [_to_job(r) for r in result.scalars()]

    async def claim_next_queued(self) -> ImportJob | None:
        result = await self._session.execute(
            select(CandleImportJobRow)
            .where(CandleImportJobRow.status == JobStatus.QUEUED.value)
            .order_by(CandleImportJobRow.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        row.status = JobStatus.RUNNING.value
        row.started_at = func.now()
        await self._session.flush()
        await self._session.refresh(row)
        return _to_job(row)

    async def requeue_running(self) -> int:
        result = await self._session.execute(
            update(CandleImportJobRow)
            .where(CandleImportJobRow.status == JobStatus.RUNNING.value)
            .values(status=JobStatus.QUEUED.value)
        )
        return int(result.rowcount or 0)  # type: ignore[attr-defined]

    async def set_progress(self, job_id: UUID, candles_imported: int) -> None:
        await self._session.execute(
            update(CandleImportJobRow)
            .where(CandleImportJobRow.id == job_id)
            .values(candles_imported=candles_imported)
        )

    async def mark_completed(self, job_id: UUID, candles_imported: int) -> None:
        await self._session.execute(
            update(CandleImportJobRow)
            .where(CandleImportJobRow.id == job_id)
            .values(
                status=JobStatus.COMPLETED.value,
                candles_imported=candles_imported,
                finished_at=func.now(),
            )
        )

    async def mark_failed(self, job_id: UUID, error: str) -> None:
        await self._session.execute(
            update(CandleImportJobRow)
            .where(CandleImportJobRow.id == job_id)
            .values(status=JobStatus.FAILED.value, error=error, finished_at=func.now())
        )

    async def commit(self) -> None:
        await self._session.commit()
