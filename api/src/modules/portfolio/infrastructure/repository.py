from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from modules.bots.infrastructure.orm import BotRow
from modules.portfolio.domain.models import PortfolioSnapshot, PortfolioState
from modules.portfolio.infrastructure.orm import BotPortfolioRow, PortfolioSnapshotRow
from modules.trading.infrastructure.orm import TradingSessionRow


class SqlAlchemyPortfolioRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, bot_id: UUID) -> PortfolioState | None:
        row = await self._session.get(BotPortfolioRow, bot_id)
        if row is None:
            return None
        return PortfolioState(
            bot_id=row.bot_id,
            cash=row.cash,
            quantity=row.quantity,
            avg_entry_price=row.avg_entry_price,
            realized_pnl=row.realized_pnl,
            fees_paid=row.fees_paid,
            stop_price=row.stop_price,
            take_profit_price=row.take_profit_price,
            reserved_cash=row.reserved_cash,
            reserved_quantity=row.reserved_quantity,
            stop_order_client_id=row.stop_order_client_id,
        )

    async def save(self, state: PortfolioState) -> None:
        values = {
            "cash": state.cash,
            "quantity": state.quantity,
            "avg_entry_price": state.avg_entry_price,
            "realized_pnl": state.realized_pnl,
            "fees_paid": state.fees_paid,
            "stop_price": state.stop_price,
            "take_profit_price": state.take_profit_price,
            "reserved_cash": state.reserved_cash,
            "reserved_quantity": state.reserved_quantity,
            "stop_order_client_id": state.stop_order_client_id,
        }
        stmt = insert(BotPortfolioRow).values(bot_id=state.bot_id, **values)
        await self._session.execute(
            stmt.on_conflict_do_update(index_elements=["bot_id"], set_=values)
        )

    async def reset(self, bot_id: UUID, initial_capital: Decimal) -> None:
        await self._session.execute(
            delete(PortfolioSnapshotRow).where(PortfolioSnapshotRow.bot_id == bot_id)
        )
        await self.save(PortfolioState.new(bot_id, initial_capital))

    async def add_snapshot(self, snapshot: PortfolioSnapshot) -> None:
        self._session.add(
            PortfolioSnapshotRow(
                bot_id=snapshot.bot_id,
                session_id=snapshot.session_id,
                taken_at=snapshot.taken_at,
                price=snapshot.price,
                cash=snapshot.cash,
                quantity=snapshot.quantity,
                equity=snapshot.equity,
            )
        )
        await self._session.flush()

    async def list_snapshots(
        self, bot_id: UUID, limit: int | None = None
    ) -> list[PortfolioSnapshot]:
        query = select(PortfolioSnapshotRow).where(PortfolioSnapshotRow.bot_id == bot_id)
        if limit is None:
            query = query.order_by(PortfolioSnapshotRow.taken_at)
            rows = list((await self._session.execute(query)).scalars())
        else:
            query = query.order_by(PortfolioSnapshotRow.taken_at.desc()).limit(limit)
            rows = list(reversed(list((await self._session.execute(query)).scalars())))
        return [
            PortfolioSnapshot(
                bot_id=r.bot_id,
                session_id=r.session_id,
                taken_at=r.taken_at,
                price=r.price,
                cash=r.cash,
                quantity=r.quantity,
                equity=r.equity,
            )
            for r in rows
        ]

    async def equity_at_or_before(self, bot_id: UUID, moment: datetime) -> Decimal | None:
        result = await self._session.execute(
            select(PortfolioSnapshotRow.equity)
            .where(PortfolioSnapshotRow.bot_id == bot_id, PortfolioSnapshotRow.taken_at <= moment)
            .order_by(PortfolioSnapshotRow.taken_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def equity_context_at(
        self, bot_id: UUID, moment: datetime
    ) -> tuple[Decimal, Decimal] | None:
        equity = await self.equity_at_or_before(bot_id, moment)
        if equity is None:
            return None
        result = await self._session.execute(
            select(func.max(PortfolioSnapshotRow.equity)).where(
                PortfolioSnapshotRow.bot_id == bot_id, PortfolioSnapshotRow.taken_at <= moment
            )
        )
        peak = result.scalar_one_or_none()
        return None if peak is None else (equity, peak)

    async def first_snapshot_equity(self, bot_id: UUID) -> Decimal | None:
        result = await self._session.execute(
            select(PortfolioSnapshotRow.equity)
            .where(PortfolioSnapshotRow.bot_id == bot_id)
            .order_by(PortfolioSnapshotRow.taken_at)
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def peak_equity(self, bot_id: UUID) -> Decimal | None:
        result = await self._session.execute(
            select(func.max(PortfolioSnapshotRow.equity)).where(
                PortfolioSnapshotRow.bot_id == bot_id
            )
        )
        return result.scalar_one_or_none()

    async def open_exposure(self, mode: str | None = None) -> tuple[int, Decimal]:
        query = select(
            func.count(),
            func.coalesce(func.sum(BotPortfolioRow.quantity * BotPortfolioRow.avg_entry_price), 0),
        ).where(BotPortfolioRow.quantity > 0)
        if mode is not None:
            query = query.join(BotRow, BotRow.id == BotPortfolioRow.bot_id).where(
                BotRow.mode == mode
            )
        count, notional = (await self._session.execute(query)).one()
        return int(count), Decimal(notional)

    async def paper_span(self, bot_id: UUID) -> tuple[datetime | None, datetime | None]:
        result = await self._session.execute(
            select(func.min(PortfolioSnapshotRow.taken_at), func.max(PortfolioSnapshotRow.taken_at))
            .join(TradingSessionRow, TradingSessionRow.id == PortfolioSnapshotRow.session_id)
            .where(PortfolioSnapshotRow.bot_id == bot_id, TradingSessionRow.mode == "paper")
        )
        first, last = result.one()
        return first, last
