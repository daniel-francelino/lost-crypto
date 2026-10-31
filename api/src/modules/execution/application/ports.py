from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from modules.execution.domain.orders import Fill, Order
from modules.strategies.domain.types import Side, SignalKind


@dataclass(frozen=True, slots=True)
class SignalRecord:
    """A strategy signal and what happened to it (explainability)."""

    id: UUID
    session_id: UUID
    bot_id: UUID
    bar_time: datetime
    side: Side
    kind: SignalKind
    reason: str
    decision: str  # approved | rejected | discarded_stale
    decision_reason: str | None
    created_at: datetime


class OrderRepository(Protocol):
    async def add_if_absent(self, order: Order) -> bool:
        """Persist the order with its fills; False if its client_order_id already exists."""
        ...

    async def update(self, order: Order, new_fills: Sequence[Fill]) -> None:
        """Persist progress (status, totals, reservation) and append the new executions."""
        ...

    async def get(self, order_id: UUID) -> Order | None: ...
    async def get_by_client_id(self, bot_id: UUID, client_order_id: str) -> Order | None: ...
    async def list_unresolved(self) -> list[Order]:
        """Orders whose outcome is not known yet (SUBMITTING / UNKNOWN), across all bots."""
        ...

    async def count_unresolved(self, bot_id: UUID) -> int: ...
    async def list_by_bot(self, bot_id: UUID, limit: int) -> list[Order]: ...
    async def list_fills(self, bot_id: UUID) -> list[Fill]: ...


class SignalRepository(Protocol):
    async def add(self, record: SignalRecord) -> None: ...
    async def list_by_bot(self, bot_id: UUID, limit: int) -> list[SignalRecord]: ...
    async def count_rejected(self, bot_id: UUID) -> int: ...
