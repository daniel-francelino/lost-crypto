from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from modules.exchanges.domain.models import PositionSide
from modules.portfolio.domain.perpetual_ledger import (
    PerpetualLedgerEntry,
    PerpetualLedgerEventKind,
    PerpetualPortfolioSnapshot,
)
from modules.portfolio.domain.perpetuals import LinearPerpetualPosition, PerpetualLedger
from modules.portfolio.infrastructure.orm import (
    PerpetualLedgerEntryRow,
    PerpetualPortfolioRow,
    PerpetualPortfolioSnapshotRow,
)


class SqlAlchemyPerpetualPortfolioRepository:
    """Persistence for the derivatives ledger; never reads or writes ``bot_portfolios``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, bot_id: UUID) -> PerpetualLedger | None:
        # Serialize account mutations inside the caller's transaction. The worker lease
        # prevents duplicate workers in normal operation; the row lock also protects API and
        # reconciliation commands from racing that worker.
        result = await self._session.execute(
            select(PerpetualPortfolioRow)
            .where(PerpetualPortfolioRow.bot_id == bot_id)
            .with_for_update()
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        position = (
            LinearPerpetualPosition(
                side=PositionSide(row.position_side),
                quantity=row.quantity,
                entry_price=row.entry_price,
                leverage=row.leverage,
                isolated_margin=row.isolated_margin,
            )
            if row.position_side is not None
            else None
        )
        return PerpetualLedger(
            bot_id=row.bot_id,
            wallet_balance=row.wallet_balance,
            position=position,
            reserved_margin=row.reserved_margin,
            realized_pnl=row.realized_pnl,
            fees_paid=row.fees_paid,
            funding_paid=row.funding_paid,
            funding_received=row.funding_received,
            mark_price=row.mark_price,
            marked_at=row.marked_at,
            mark_source=row.mark_source,
            maintenance_margin_rate=row.maintenance_margin_rate,
            exchange_position_id=row.exchange_position_id,
            exchange_liquidation_price=row.exchange_liquidation_price,
            reconciled_at=row.reconciled_at,
        )

    async def save(self, ledger: PerpetualLedger) -> None:
        position = ledger.position
        values = {
            "wallet_balance": ledger.wallet_balance,
            "reserved_margin": ledger.reserved_margin,
            "realized_pnl": ledger.realized_pnl,
            "fees_paid": ledger.fees_paid,
            "funding_paid": ledger.funding_paid,
            "funding_received": ledger.funding_received,
            "position_side": position.side.value if position else None,
            "quantity": position.quantity if position else Decimal(0),
            "entry_price": position.entry_price if position else Decimal(0),
            "leverage": position.leverage if position else 1,
            "isolated_margin": position.isolated_margin if position else Decimal(0),
            "mark_price": ledger.mark_price,
            "marked_at": ledger.marked_at,
            "mark_source": ledger.mark_source,
            "maintenance_margin_rate": ledger.maintenance_margin_rate,
            "exchange_position_id": ledger.exchange_position_id,
            "exchange_liquidation_price": ledger.exchange_liquidation_price,
            "reconciled_at": ledger.reconciled_at,
        }
        statement = insert(PerpetualPortfolioRow).values(bot_id=ledger.bot_id, **values)
        await self._session.execute(
            statement.on_conflict_do_update(index_elements=["bot_id"], set_=values)
        )

    async def append_entry(self, entry: PerpetualLedgerEntry) -> bool:
        statement = (
            insert(PerpetualLedgerEntryRow)
            .values(
                id=entry.id,
                bot_id=entry.bot_id,
                occurred_at=entry.occurred_at,
                kind=entry.kind.value,
                wallet_delta=entry.wallet_delta,
                isolated_margin_delta=entry.isolated_margin_delta,
                realized_pnl_delta=entry.realized_pnl_delta,
                fee=entry.fee,
                funding=entry.funding,
                quantity=entry.quantity,
                side=entry.side.value if entry.side else None,
                price=entry.price,
                source=entry.source,
                external_reference=entry.external_reference,
            )
            .on_conflict_do_nothing()
            .returning(PerpetualLedgerEntryRow.id)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none() is not None

    async def list_entries(
        self, bot_id: UUID, start: datetime | None = None, end: datetime | None = None
    ) -> list[PerpetualLedgerEntry]:
        query = select(PerpetualLedgerEntryRow).where(PerpetualLedgerEntryRow.bot_id == bot_id)
        if start is not None:
            query = query.where(PerpetualLedgerEntryRow.occurred_at >= start)
        if end is not None:
            query = query.where(PerpetualLedgerEntryRow.occurred_at < end)
        result = await self._session.execute(query.order_by(PerpetualLedgerEntryRow.occurred_at))
        rows = result.scalars()
        return [
            PerpetualLedgerEntry(
                id=row.id,
                bot_id=row.bot_id,
                occurred_at=row.occurred_at,
                kind=PerpetualLedgerEventKind(row.kind),
                wallet_delta=row.wallet_delta,
                isolated_margin_delta=row.isolated_margin_delta,
                realized_pnl_delta=row.realized_pnl_delta,
                fee=row.fee,
                funding=row.funding,
                quantity=row.quantity,
                side=PositionSide(row.side) if row.side else None,
                price=row.price,
                source=row.source,
                external_reference=row.external_reference,
            )
            for row in rows
        ]

    async def add_snapshot(self, snapshot: PerpetualPortfolioSnapshot) -> None:
        self._session.add(
            PerpetualPortfolioSnapshotRow(
                bot_id=snapshot.bot_id,
                session_id=snapshot.session_id,
                taken_at=snapshot.taken_at,
                mark_price=snapshot.mark_price,
                wallet_balance=snapshot.wallet_balance,
                isolated_margin=snapshot.isolated_margin,
                position_side=snapshot.position_side.value if snapshot.position_side else None,
                quantity=snapshot.quantity,
                entry_price=snapshot.entry_price,
                equity=snapshot.equity,
                unrealized_pnl=snapshot.unrealized_pnl,
                funding_paid=snapshot.funding_paid,
                funding_received=snapshot.funding_received,
                mark_source=snapshot.mark_source,
            )
        )
        await self._session.flush()

    async def list_snapshots(
        self, bot_id: UUID, limit: int | None = None
    ) -> list[PerpetualPortfolioSnapshot]:
        query = select(PerpetualPortfolioSnapshotRow).where(
            PerpetualPortfolioSnapshotRow.bot_id == bot_id
        )
        if limit is not None:
            query = query.order_by(PerpetualPortfolioSnapshotRow.taken_at.desc()).limit(limit)
            rows = list(reversed(list((await self._session.execute(query)).scalars())))
        else:
            result = await self._session.execute(
                query.order_by(PerpetualPortfolioSnapshotRow.taken_at)
            )
            rows = list(result.scalars())
        return [
            PerpetualPortfolioSnapshot(
                bot_id=row.bot_id,
                session_id=row.session_id,
                taken_at=row.taken_at,
                mark_price=row.mark_price,
                wallet_balance=row.wallet_balance,
                isolated_margin=row.isolated_margin,
                position_side=PositionSide(row.position_side) if row.position_side else None,
                quantity=row.quantity,
                entry_price=row.entry_price,
                equity=row.equity,
                unrealized_pnl=row.unrealized_pnl,
                funding_paid=row.funding_paid,
                funding_received=row.funding_received,
                mark_source=row.mark_source,
            )
            for row in rows
        ]

    async def reset(self, bot_id: UUID, initial_capital: Decimal) -> None:
        await self._session.execute(
            delete(PerpetualPortfolioSnapshotRow).where(
                PerpetualPortfolioSnapshotRow.bot_id == bot_id
            )
        )
        await self._session.execute(
            delete(PerpetualLedgerEntryRow).where(PerpetualLedgerEntryRow.bot_id == bot_id)
        )
        await self.save(PerpetualLedger.new(bot_id, initial_capital))
