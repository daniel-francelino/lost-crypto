from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from modules.trading.application.parity_store import ParityRun
from modules.trading.domain.models import SessionStatus, TradingSession
from modules.trading.infrastructure.orm import ParityRunRow, TradingSessionRow


def _to_session(row: TradingSessionRow) -> TradingSession:
    return TradingSession(
        id=row.id,
        bot_id=row.bot_id,
        config_version=row.config_version,
        mode=row.mode,
        status=SessionStatus(row.status),
        started_at=row.started_at,
        strategy_state=row.strategy_state,
        last_processed_bar_time=row.last_processed_bar_time,
        ended_at=row.ended_at,
        end_reason=row.end_reason,
    )


class SqlAlchemySessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_active(self, bot_id: UUID) -> TradingSession | None:
        result = await self._session.execute(
            select(TradingSessionRow).where(
                TradingSessionRow.bot_id == bot_id,
                TradingSessionRow.status == SessionStatus.ACTIVE.value,
            )
        )
        row = result.scalar_one_or_none()
        return None if row is None else _to_session(row)

    async def latest(self, bot_id: UUID, mode: str | None = None) -> TradingSession | None:
        """The most recent session of the bot (of ``mode``, when given), active or ended."""
        query = select(TradingSessionRow).where(TradingSessionRow.bot_id == bot_id)
        if mode is not None:
            query = query.where(TradingSessionRow.mode == mode)
        result = await self._session.execute(
            query.order_by(TradingSessionRow.started_at.desc()).limit(1)
        )
        row = result.scalar_one_or_none()
        return None if row is None else _to_session(row)

    async def add(self, session: TradingSession) -> None:
        self._session.add(
            TradingSessionRow(
                id=session.id,
                bot_id=session.bot_id,
                config_version=session.config_version,
                mode=session.mode,
                status=session.status.value,
                started_at=session.started_at,
                strategy_state=session.strategy_state,
                last_processed_bar_time=session.last_processed_bar_time,
            )
        )
        await self._session.flush()

    async def save_progress(
        self, session_id: UUID, strategy_state: dict[str, Any], last_bar_time: datetime
    ) -> None:
        await self._session.execute(
            update(TradingSessionRow)
            .where(TradingSessionRow.id == session_id)
            .values(strategy_state=strategy_state, last_processed_bar_time=last_bar_time)
        )

    async def end(self, session_id: UUID, reason: str) -> None:
        await self._session.execute(
            update(TradingSessionRow)
            .where(TradingSessionRow.id == session_id)
            .values(status=SessionStatus.ENDED.value, end_reason=reason, ended_at=func.now())
        )


def _to_parity(row: ParityRunRow) -> ParityRun:
    return ParityRun(
        id=row.id,
        bot_id=row.bot_id,
        session_id=row.session_id,
        status=row.status,
        created_at=row.created_at,
        finished_at=row.finished_at,
        unexplained=row.unexplained,
        summary=row.summary,
        error=row.error,
    )


class SqlAlchemyParityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, run: ParityRun) -> None:
        self._session.add(
            ParityRunRow(
                id=run.id,
                bot_id=run.bot_id,
                session_id=run.session_id,
                status=run.status,
                created_at=run.created_at,
            )
        )
        await self._session.flush()

    async def latest(self, bot_id: UUID) -> ParityRun | None:
        result = await self._session.execute(
            select(ParityRunRow)
            .where(ParityRunRow.bot_id == bot_id)
            .order_by(ParityRunRow.created_at.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return None if row is None else _to_parity(row)

    async def latest_completed(self, bot_id: UUID) -> ParityRun | None:
        result = await self._session.execute(
            select(ParityRunRow)
            .where(ParityRunRow.bot_id == bot_id, ParityRunRow.status == "completed")
            .order_by(ParityRunRow.created_at.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return None if row is None else _to_parity(row)

    async def claim_next_queued(self) -> ParityRun | None:
        result = await self._session.execute(
            select(ParityRunRow)
            .where(ParityRunRow.status == "queued")
            .order_by(ParityRunRow.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        row.status = "running"
        await self._session.flush()
        return _to_parity(row)

    async def finish(
        self,
        run_id: UUID,
        *,
        status: str,
        finished_at: datetime,
        session_id: UUID | None = None,
        unexplained: int | None = None,
        summary: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        await self._session.execute(
            update(ParityRunRow)
            .where(ParityRunRow.id == run_id)
            .values(
                status=status,
                finished_at=finished_at,
                session_id=session_id,
                unexplained=unexplained,
                summary=summary,
                error=error,
            )
        )
