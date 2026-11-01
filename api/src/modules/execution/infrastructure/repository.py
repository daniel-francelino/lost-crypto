from collections.abc import Sequence
from uuid import UUID, uuid4

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from modules.execution.application.ports import SignalRecord
from modules.execution.domain.orders import Fill, Order, OrderStatus
from modules.execution.infrastructure.orm import OrderFillRow, OrderRow, TradingSignalRow
from modules.strategies.domain.types import Side, SignalKind

_UNRESOLVED = (OrderStatus.SUBMITTING.value, OrderStatus.UNKNOWN.value)


def _to_fill(row: OrderFillRow) -> Fill:
    trade_id = row.venue_trade_id
    return Fill(
        row.time,
        Side(row.side),
        row.quantity,
        row.price,
        row.fee,
        row.fee_base,
        None if trade_id.startswith("sim-") else trade_id,
    )


def _to_order(row: OrderRow, fills: Sequence[Fill] = ()) -> Order:
    return Order(
        id=row.id,
        bot_id=row.bot_id,
        session_id=row.session_id,
        client_order_id=row.client_order_id,
        symbol=row.symbol,
        side=Side(row.side),
        quantity=row.quantity,
        bar_time=row.bar_time,
        created_at=row.created_at,
        status=OrderStatus(row.status),
        filled_quantity=row.filled_quantity,
        avg_fill_price=row.avg_fill_price,
        reject_reason=row.reject_reason,
        fills=list(fills),
        order_type=row.type,
        stop_price=row.stop_price,
        exchange_order_id=row.exchange_order_id,
        reserved_cash=row.reserved_cash,
        reserved_quantity=row.reserved_quantity,
        planned_stop_price=row.planned_stop_price,
        planned_take_profit_price=row.planned_take_profit_price,
        reference_price=row.reference_price,
        submitted_at=row.submitted_at,
        first_fill_at=row.first_fill_at,
    )


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
                type=order.order_type,
                quantity=order.quantity,
                filled_quantity=order.filled_quantity,
                avg_fill_price=order.avg_fill_price,
                status=order.status.value,
                reject_reason=order.reject_reason,
                exchange_order_id=order.exchange_order_id,
                stop_price=order.stop_price,
                reserved_cash=order.reserved_cash,
                reserved_quantity=order.reserved_quantity,
                planned_stop_price=order.planned_stop_price,
                planned_take_profit_price=order.planned_take_profit_price,
                bar_time=order.bar_time,
                created_at=order.created_at,
                reference_price=order.reference_price,
                submitted_at=order.submitted_at,
                first_fill_at=order.first_fill_at,
            )
            .on_conflict_do_nothing(index_elements=["bot_id", "client_order_id"])
            .returning(OrderRow.id)
        )
        inserted = (await self._session.execute(stmt)).scalar_one_or_none()
        if inserted is None:
            return False
        await self._add_fills(order.id, order.fills, existing=0)
        await self._session.flush()
        return True

    async def update(self, order: Order, new_fills: Sequence[Fill]) -> None:
        """Persist the order's progress (status, totals, reservation) and its new executions."""
        stored = await self._session.scalar(
            select(func.count()).select_from(OrderFillRow).where(OrderFillRow.order_id == order.id)
        )
        await self._add_fills(order.id, new_fills, existing=int(stored or 0))
        await self._session.execute(
            update(OrderRow)
            .where(OrderRow.id == order.id)
            .values(
                status=order.status.value,
                filled_quantity=order.filled_quantity,
                avg_fill_price=order.avg_fill_price,
                reject_reason=order.reject_reason,
                exchange_order_id=order.exchange_order_id,
                reserved_cash=order.reserved_cash,
                reserved_quantity=order.reserved_quantity,
                submitted_at=order.submitted_at,
                first_fill_at=order.first_fill_at,
            )
        )
        await self._session.flush()

    async def get(self, order_id: UUID) -> Order | None:
        row = await self._session.get(OrderRow, order_id)
        return await self._with_fills(row) if row else None

    async def get_by_client_id(self, bot_id: UUID, client_order_id: str) -> Order | None:
        result = await self._session.execute(
            select(OrderRow).where(
                OrderRow.bot_id == bot_id, OrderRow.client_order_id == client_order_id
            )
        )
        row = result.scalar_one_or_none()
        return await self._with_fills(row) if row else None

    async def list_unresolved(self) -> list[Order]:
        result = await self._session.execute(
            select(OrderRow).where(OrderRow.status.in_(_UNRESOLVED)).order_by(OrderRow.created_at)
        )
        return [await self._with_fills(r) for r in result.scalars()]

    async def count_unresolved(self, bot_id: UUID) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(OrderRow)
            .where(OrderRow.bot_id == bot_id, OrderRow.status.in_(_UNRESOLVED))
        )
        return int(result.scalar_one())

    async def count_by_bot(self, bot_id: UUID) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(OrderRow).where(OrderRow.bot_id == bot_id)
        )
        return int(result.scalar_one())

    async def list_by_bot(self, bot_id: UUID, limit: int, offset: int = 0) -> list[Order]:
        result = await self._session.execute(
            select(OrderRow)
            .where(OrderRow.bot_id == bot_id)
            .order_by(OrderRow.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return [_to_order(r) for r in result.scalars()]

    async def list_fills(self, bot_id: UUID) -> list[Fill]:
        result = await self._session.execute(
            select(OrderFillRow)
            .join(OrderRow, OrderRow.id == OrderFillRow.order_id)
            .where(OrderRow.bot_id == bot_id)
            .order_by(OrderFillRow.time, OrderFillRow.id)
        )
        return [_to_fill(r) for r in result.scalars()]

    async def _with_fills(self, row: OrderRow) -> Order:
        result = await self._session.execute(
            select(OrderFillRow).where(OrderFillRow.order_id == row.id).order_by(OrderFillRow.time)
        )
        return _to_order(row, [_to_fill(f) for f in result.scalars()])

    async def _add_fills(self, order_id: UUID, fills: Sequence[Fill], existing: int) -> None:
        for i, fill in enumerate(fills):
            self._session.add(
                OrderFillRow(
                    id=uuid4(),
                    order_id=order_id,
                    venue_trade_id=fill.trade_id or f"sim-{existing + i}",
                    time=fill.time,
                    side=fill.side.value,
                    quantity=fill.quantity,
                    price=fill.price,
                    fee=fill.fee,
                    fee_base=fill.fee_base,
                )
            )


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

    async def count_by_bot(self, bot_id: UUID) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(TradingSignalRow)
            .where(TradingSignalRow.bot_id == bot_id)
        )
        return int(result.scalar_one())

    async def list_by_bot(self, bot_id: UUID, limit: int, offset: int = 0) -> list[SignalRecord]:
        result = await self._session.execute(
            select(TradingSignalRow)
            .where(TradingSignalRow.bot_id == bot_id)
            .order_by(TradingSignalRow.created_at.desc())
            .limit(limit)
            .offset(offset)
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
