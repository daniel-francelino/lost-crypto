from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from modules.execution.application.ports import SignalRecord
from modules.execution.domain.orders import Fill, Order, OrderStatus
from modules.execution.infrastructure.orm import OrderFillRow, OrderRow, TradingSignalRow
from modules.strategies.domain.types import Side, SignalKind


class SqlAlchemyOrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_if_absent(self, order: Order) -> bool:
        stmt = (
            insert(OrderRow)
            .values(
                id=order.id,
                bot_id=order.bot_id,
                session_id=order.session_id,
                client_order_id=order.client_order_id,
                symbol=order.symbol,
                side=order.side.value,
                type="market",
                quantity=order.quantity,
                filled_quantity=order.filled_quantity,
                avg_fill_price=order.avg_fill_price,
                status=order.status.value,
                reject_reason=order.reject_reason,
                bar_time=order.bar_time,
                created_at=order.created_at,
            )
            .on_conflict_do_nothing(index_elements=["bot_id", "client_order_id"])
            .returning(OrderRow.id)
        )
        inserted = (await self._session.execute(stmt)).scalar_one_or_none()
        if inserted is None:
            return False
        for i, fill in enumerate(order.fills):
            self._session.add(
                OrderFillRow(
                    id=uuid4(),
                    order_id=order.id,
                    venue_trade_id=f"paper-{i}",
                    time=fill.time,
                    side=fill.side.value,
                    quantity=fill.quantity,
                    price=fill.price,
                    fee=fill.fee,
                )
            )
        await self._session.flush()
        return True

    async def list_by_bot(self, bot_id: UUID, limit: int) -> list[Order]:
        result = await self._session.execute(
            select(OrderRow)
            .where(OrderRow.bot_id == bot_id)
            .order_by(OrderRow.created_at.desc())
            .limit(limit)
        )
        return [
            Order(
                id=r.id,
                bot_id=r.bot_id,
                session_id=r.session_id,
                client_order_id=r.client_order_id,
                symbol=r.symbol,
                side=Side(r.side),
                quantity=r.quantity,
                bar_time=r.bar_time,
                created_at=r.created_at,
                status=OrderStatus(r.status),
                filled_quantity=r.filled_quantity,
                avg_fill_price=r.avg_fill_price,
                reject_reason=r.reject_reason,
            )
            for r in result.scalars()
        ]

    async def list_fills(self, bot_id: UUID) -> list[Fill]:
        result = await self._session.execute(
            select(OrderFillRow)
            .join(OrderRow, OrderRow.id == OrderFillRow.order_id)
            .where(OrderRow.bot_id == bot_id)
            .order_by(OrderFillRow.time, OrderFillRow.id)
        )
        return [Fill(r.time, Side(r.side), r.quantity, r.price, r.fee) for r in result.scalars()]


class SqlAlchemySignalRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: SignalRecord) -> None:
        self._session.add(
            TradingSignalRow(
                id=record.id,
                session_id=record.session_id,
                bot_id=record.bot_id,
                bar_time=record.bar_time,
                side=record.side.value,
                kind=record.kind.value,
                reason=record.reason,
                decision=record.decision,
                decision_reason=record.decision_reason,
                created_at=record.created_at,
            )
        )
        await self._session.flush()

    async def list_by_bot(self, bot_id: UUID, limit: int) -> list[SignalRecord]:
        result = await self._session.execute(
            select(TradingSignalRow)
            .where(TradingSignalRow.bot_id == bot_id)
            .order_by(TradingSignalRow.created_at.desc())
            .limit(limit)
        )
        return [
            SignalRecord(
                id=r.id,
                session_id=r.session_id,
                bot_id=r.bot_id,
                bar_time=r.bar_time,
                side=Side(r.side),
                kind=SignalKind(r.kind),
                reason=r.reason,
                decision=r.decision,
                decision_reason=r.decision_reason,
                created_at=r.created_at,
            )
            for r in result.scalars()
        ]

    async def count_rejected(self, bot_id: UUID) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(TradingSignalRow)
            .where(TradingSignalRow.bot_id == bot_id, TradingSignalRow.decision == "rejected")
        )
        return int(result.scalar_one())
