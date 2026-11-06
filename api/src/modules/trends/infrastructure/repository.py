from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from modules.market_data.application.ports import CandleRepository
from modules.market_data.domain.trend import Trend, TrendFrame
from modules.market_data.infrastructure.repository import SqlAlchemyCandleRepository
from modules.trends.domain.models import FrameProgress, TrendRecord, WatchedSymbol
from modules.trends.infrastructure.orm import TrendReadingRow, TrendStateRow, TrendSymbolRow

_UPSERT_CHUNK = 500
_VALUE_COLUMNS = (
    "trend",
    "previous_trend",
    "close",
    "ema_fast",
    "ema_slow",
    "ema_distance_pct",
    "slow_slope_pct",
    "adx",
    "atr",
    "structure",
    "checks",
    "confirmed",
    "computed_at",
)


def _symbol(row: TrendSymbolRow) -> WatchedSymbol:
    return WatchedSymbol(row.id, row.exchange, row.symbol, row.active, row.created_at)


def _record(row: TrendReadingRow) -> TrendRecord:
    return TrendRecord(
        row.exchange,
        row.symbol,
        TrendFrame(row.frame),
        row.bar_open_time,
        Trend(row.trend),
        None if row.previous_trend is None else Trend(row.previous_trend),
        row.close,
        row.ema_fast,
        row.ema_slow,
        row.ema_distance_pct,
        row.slow_slope_pct,
        row.adx,
        row.atr,
        None if row.structure is None else Trend(row.structure),
        dict(row.checks),
        row.confirmed,
        row.computed_at,
    )


class SqlAlchemyTrendRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_symbols(self, *, active_only: bool) -> list[WatchedSymbol]:
        query = select(TrendSymbolRow).order_by(TrendSymbolRow.exchange, TrendSymbolRow.symbol)
        if active_only:
            query = query.where(TrendSymbolRow.active.is_(True))
        return [_symbol(r) for r in (await self._session.execute(query)).scalars()]

    async def get_symbol(self, symbol_id: UUID) -> WatchedSymbol | None:
        row = await self._session.get(TrendSymbolRow, symbol_id)
        return None if row is None else _symbol(row)

    async def find_symbol(self, exchange: str, symbol: str) -> WatchedSymbol | None:
        result = await self._session.execute(
            select(TrendSymbolRow).where(
                TrendSymbolRow.exchange == exchange, TrendSymbolRow.symbol == symbol
            )
        )
        row = result.scalar_one_or_none()
        return None if row is None else _symbol(row)

    async def add_symbol(self, symbol: WatchedSymbol) -> None:
        self._session.add(
            TrendSymbolRow(
                id=symbol.id,
                exchange=symbol.exchange,
                symbol=symbol.symbol,
                active=symbol.active,
                created_at=symbol.created_at,
            )
        )
        await self._session.flush()

    async def set_active(self, symbol_id: UUID, active: bool) -> bool:
        row = await self._session.get(TrendSymbolRow, symbol_id)
        if row is None:
            return False
        await self._session.execute(
            update(TrendSymbolRow).where(TrendSymbolRow.id == symbol_id).values(active=active)
        )
        return True

    async def get_progress(self, exchange: str, symbol: str) -> dict[TrendFrame, FrameProgress]:
        result = await self._session.execute(
            select(TrendStateRow).where(
                TrendStateRow.exchange == exchange, TrendStateRow.symbol == symbol
            )
        )
        return {
            TrendFrame(r.frame): FrameProgress(
                TrendFrame(r.frame), r.last_bar_open_time, r.settings_key, dict(r.state)
            )
            for r in result.scalars()
        }

    async def save_progress(
        self, exchange: str, symbol: str, progress: FrameProgress, now: datetime
    ) -> None:
        values = {
            "last_bar_open_time": progress.last_bar_open_time,
            "settings_key": progress.settings_key,
            "state": progress.state,
            "updated_at": now,
        }
        stmt = insert(TrendStateRow).values(
            exchange=exchange, symbol=symbol, frame=progress.frame.value, **values
        )
        await self._session.execute(
            stmt.on_conflict_do_update(index_elements=["exchange", "symbol", "frame"], set_=values)
        )

    async def reset_frame(self, exchange: str, symbol: str, frame: TrendFrame) -> None:
        await self._session.execute(
            delete(TrendStateRow).where(
                TrendStateRow.exchange == exchange,
                TrendStateRow.symbol == symbol,
                TrendStateRow.frame == frame.value,
            )
        )
        await self._session.execute(
            delete(TrendReadingRow).where(
                TrendReadingRow.exchange == exchange,
                TrendReadingRow.symbol == symbol,
                TrendReadingRow.frame == frame.value,
            )
        )

    async def upsert_records(self, records: Sequence[TrendRecord]) -> int:
        for i in range(0, len(records), _UPSERT_CHUNK):
            rows = [
                {
                    "exchange": r.exchange,
                    "symbol": r.symbol,
                    "frame": r.frame.value,
                    "bar_open_time": r.bar_open_time,
                    "trend": r.trend.value,
                    "previous_trend": None if r.previous_trend is None else r.previous_trend.value,
                    "close": r.close,
                    "ema_fast": r.ema_fast,
                    "ema_slow": r.ema_slow,
                    "ema_distance_pct": r.ema_distance_pct,
                    "slow_slope_pct": r.slow_slope_pct,
                    "adx": r.adx,
                    "atr": r.atr,
                    "structure": None if r.structure is None else r.structure.value,
                    "checks": r.checks,
                    "confirmed": r.confirmed,
                    "computed_at": r.computed_at,
                }
                for r in records[i : i + _UPSERT_CHUNK]
            ]
            stmt = insert(TrendReadingRow).values(rows)
            await self._session.execute(
                stmt.on_conflict_do_update(
                    index_elements=["exchange", "symbol", "frame", "bar_open_time"],
                    set_={c: stmt.excluded[c] for c in _VALUE_COLUMNS},
                )
            )
        return len(records)

    async def latest(self, exchange: str, symbol: str) -> list[TrendRecord]:
        result = await self._session.execute(
            select(TrendReadingRow)
            .where(TrendReadingRow.exchange == exchange, TrendReadingRow.symbol == symbol)
            .distinct(TrendReadingRow.frame)
            .order_by(TrendReadingRow.frame, TrendReadingRow.bar_open_time.desc())
        )
        order = {frame.value: i for i, frame in enumerate(TrendFrame)}
        return sorted((_record(r) for r in result.scalars()), key=lambda r: order[r.frame.value])

    async def history(
        self,
        exchange: str,
        symbol: str,
        frame: TrendFrame,
        limit: int,
        before: datetime | None = None,
    ) -> list[TrendRecord]:
        query = (
            select(TrendReadingRow)
            .where(
                TrendReadingRow.exchange == exchange,
                TrendReadingRow.symbol == symbol,
                TrendReadingRow.frame == frame.value,
            )
            .order_by(TrendReadingRow.bar_open_time.desc())
            .limit(limit)
        )
        if before is not None:
            query = query.where(TrendReadingRow.bar_open_time < before)
        return [_record(r) for r in (await self._session.execute(query)).scalars()]


class SqlAlchemyTrendStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._candles = SqlAlchemyCandleRepository(session)
        self._trends = SqlAlchemyTrendRepository(session)

    @property
    def candles(self) -> CandleRepository:
        return self._candles

    @property
    def trends(self) -> SqlAlchemyTrendRepository:
        return self._trends

    async def commit(self) -> None:
        await self._session.commit()
