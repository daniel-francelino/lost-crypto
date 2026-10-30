from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from modules.trading.domain.models import SessionStatus, TradingSession
from modules.trading.infrastructure.orm import TradingSessionRow


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
        if row is None:
            return None
        return TradingSession(
            id=row.id,
            bot_id=row.bot_id,
            config_version=row.config_version,
            status=SessionStatus(row.status),
            started_at=row.started_at,
            strategy_state=row.strategy_state,
            last_processed_bar_time=row.last_processed_bar_time,
            ended_at=row.ended_at,
            end_reason=row.end_reason,
        )

    async def add(self, session: TradingSession) -> None:
        self._session.add(
            TradingSessionRow(
                id=session.id,
                bot_id=session.bot_id,
                config_version=session.config_version,
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
