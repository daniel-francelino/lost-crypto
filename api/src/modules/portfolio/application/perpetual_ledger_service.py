"""Transactional commands for the isolated perpetual portfolio.

The caller owns the unit of work and commits after this service returns. Each successful
command appends its immutable event and updates the projection in the same DB transaction.
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from core.errors import DomainError
from modules.exchanges.domain.models import PositionSide
from modules.portfolio.application.perpetual_ports import PerpetualPortfolioRepository
from modules.portfolio.domain.perpetual_ledger import (
    PerpetualLedgerEntry,
    PerpetualLedgerEventKind,
)
from modules.portfolio.domain.perpetuals import PerpetualLedger


class PerpetualLedgerService:
    """Apply idempotent position and funding changes without touching the spot ledger."""

    def __init__(self, repository: PerpetualPortfolioRepository) -> None:
        self._repository = repository

    async def open_position(
        self,
        bot_id: UUID,
        *,
        side: PositionSide,
        quantity: Decimal,
        price: Decimal,
        leverage: int,
        fee: Decimal,
        occurred_at: datetime,
        external_reference: str,
        source: str = "worker",
    ) -> bool:
        ledger = await self._require_ledger(bot_id)
        position = ledger.open_position(side, quantity, price, leverage, fee)
        inserted = await self._repository.append_entry(
            PerpetualLedgerEntry(
                id=uuid4(),
                bot_id=bot_id,
                occurred_at=occurred_at,
                kind=PerpetualLedgerEventKind.POSITION_OPENED,
                wallet_delta=-(position.isolated_margin + fee),
                isolated_margin_delta=position.isolated_margin,
                fee=fee,
                quantity=quantity,
                side=side,
                price=price,
                source=source,
                external_reference=external_reference,
            )
        )
        if inserted:
            await self._repository.save(ledger)
        return inserted

    async def close_position(
        self,
        bot_id: UUID,
        *,
        quantity: Decimal,
        price: Decimal,
        fee: Decimal,
        occurred_at: datetime,
        external_reference: str,
        source: str = "worker",
        liquidated: bool = False,
    ) -> bool:
        ledger = await self._require_ledger(bot_id)
        position = ledger.position
        if position is None:
            raise DomainError("there is no open perpetual position")
        released = position.isolated_margin * quantity / position.quantity
        side = position.side
        realized = ledger.close_position(quantity, price, fee)
        inserted = await self._repository.append_entry(
            PerpetualLedgerEntry(
                id=uuid4(),
                bot_id=bot_id,
                occurred_at=occurred_at,
                kind=(
                    PerpetualLedgerEventKind.LIQUIDATED
                    if liquidated
                    else PerpetualLedgerEventKind.POSITION_REDUCED
                ),
                wallet_delta=released + realized,
                isolated_margin_delta=-released,
                realized_pnl_delta=realized,
                fee=fee,
                quantity=quantity,
                side=side,
                price=price,
                source=source,
                external_reference=external_reference,
            )
        )
        if inserted:
            await self._repository.save(ledger)
        return inserted

    async def settle_funding(
        self,
        bot_id: UUID,
        *,
        mark_price: Decimal,
        funding_rate: Decimal,
        occurred_at: datetime,
        external_reference: str,
        source: str = "exchange",
    ) -> bool:
        ledger = await self._require_ledger(bot_id)
        position = ledger.position
        if position is None:
            return False
        quantity, side = position.quantity, position.side
        payment = ledger.apply_funding(mark_price, funding_rate)
        inserted = await self._repository.append_entry(
            PerpetualLedgerEntry(
                id=uuid4(),
                bot_id=bot_id,
                occurred_at=occurred_at,
                kind=PerpetualLedgerEventKind.FUNDING_SETTLED,
                isolated_margin_delta=payment,
                funding=payment,
                quantity=quantity,
                side=side,
                price=mark_price,
                source=source,
                external_reference=external_reference,
            )
        )
        if inserted:
            await self._repository.save(ledger)
        return inserted

    async def _require_ledger(self, bot_id: UUID) -> PerpetualLedger:
        ledger = await self._repository.get(bot_id)
        if ledger is None:
            raise DomainError("perpetual portfolio has not been initialized")
        return ledger
