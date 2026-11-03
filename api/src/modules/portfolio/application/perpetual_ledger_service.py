"""Transactional commands for the isolated perpetual portfolio.

The caller owns the unit of work and commits after this service returns. Each successful
command appends its immutable event and updates the projection in the same DB transaction.
"""

from dataclasses import replace
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

    async def reserve_margin(
        self,
        bot_id: UUID,
        *,
        amount: Decimal,
        occurred_at: datetime,
        external_reference: str,
        source: str = "worker",
    ) -> bool:
        ledger = await self._require_ledger(bot_id)
        if await self._repository.has_entry(bot_id, external_reference):
            return False
        ledger.reserve(amount)
        inserted = await self._repository.append_entry(
            PerpetualLedgerEntry(
                id=uuid4(),
                bot_id=bot_id,
                occurred_at=occurred_at,
                kind=PerpetualLedgerEventKind.MARGIN_RESERVED,
                reserved_margin_delta=amount,
                source=source,
                external_reference=external_reference,
            )
        )
        if inserted:
            await self._repository.save(ledger)
        return inserted

    async def release_margin(
        self,
        bot_id: UUID,
        *,
        amount: Decimal,
        occurred_at: datetime,
        external_reference: str,
        source: str = "worker",
    ) -> bool:
        ledger = await self._require_ledger(bot_id)
        if await self._repository.has_entry(bot_id, external_reference):
            return False
        ledger.release(amount)
        inserted = await self._repository.append_entry(
            PerpetualLedgerEntry(
                id=uuid4(),
                bot_id=bot_id,
                occurred_at=occurred_at,
                kind=PerpetualLedgerEventKind.MARGIN_RELEASED,
                reserved_margin_delta=-amount,
                source=source,
                external_reference=external_reference,
            )
        )
        if inserted:
            await self._repository.save(ledger)
        return inserted

    async def open_position(
        self,
        bot_id: UUID,
        *,
        side: PositionSide,
        quantity: Decimal,
        price: Decimal,
        leverage: int,
        fee: Decimal,
        stop_price: Decimal | None = None,
        take_profit_price: Decimal | None = None,
        occurred_at: datetime,
        external_reference: str,
        source: str = "worker",
    ) -> bool:
        ledger = await self._require_ledger(bot_id)
        if await self._repository.has_entry(bot_id, external_reference):
            return False
        position = ledger.open_position(
            side, quantity, price, leverage, fee, stop_price, take_profit_price
        )
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
        if await self._repository.has_entry(bot_id, external_reference):
            return False
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
        if await self._repository.has_entry(bot_id, external_reference):
            return False
        position = ledger.position
        if position is None:
            return False
        quantity, side = position.quantity, position.side
        wallet_before = ledger.wallet_balance
        margin_before = position.isolated_margin
        realized_before = ledger.realized_pnl
        fees_before = ledger.fees_paid
        payment = ledger.apply_funding(mark_price, funding_rate)
        position_after = ledger.position
        liquidated = position_after is None
        margin_delta = (
            -margin_before
            if position_after is None
            else position_after.isolated_margin - margin_before
        )
        inserted = await self._repository.append_entry(
            PerpetualLedgerEntry(
                id=uuid4(),
                bot_id=bot_id,
                occurred_at=occurred_at,
                kind=(
                    PerpetualLedgerEventKind.LIQUIDATED
                    if liquidated
                    else PerpetualLedgerEventKind.FUNDING_SETTLED
                ),
                wallet_delta=ledger.wallet_balance - wallet_before,
                isolated_margin_delta=margin_delta,
                realized_pnl_delta=ledger.realized_pnl - realized_before,
                fee=ledger.fees_paid - fees_before,
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

    async def settle_exchange_funding_income(
        self,
        bot_id: UUID,
        *,
        amount: Decimal,
        isolated_margin_after: Decimal,
        occurred_at: datetime,
        transaction_id: str,
        source: str = "binance_user_stream",
    ) -> bool:
        """Apply one exchange-settled funding transaction, exactly once.

        The exchange's isolated-wallet value determines how much of the signed cash flow was
        applied to position margin. The remainder is applied to the ledger wallet, so total
        equity changes by the actual income amount exactly once.
        """
        if not transaction_id.strip() or not amount.is_finite():
            raise DomainError("exchange funding income identity or amount is invalid")
        if isolated_margin_after < 0 or not isolated_margin_after.is_finite():
            raise DomainError("exchange isolated margin is invalid")
        if occurred_at.tzinfo is None:
            raise DomainError("exchange funding timestamp must be timezone-aware")
        external_reference = f"binance:funding:{transaction_id}"
        if await self._repository.has_entry(bot_id, external_reference):
            return False
        ledger = await self._require_ledger(bot_id)
        position = ledger.position
        if position is None:
            raise DomainError("cannot settle exchange funding without the tracked position")
        if isolated_margin_after <= 0:
            raise DomainError("exchange funding left no isolated margin; reconcile liquidation")
        margin_delta = isolated_margin_after - position.isolated_margin
        wallet_delta = amount - margin_delta
        updated_wallet = ledger.wallet_balance + wallet_delta
        if updated_wallet < ledger.reserved_margin:
            raise DomainError(
                "exchange funding would consume collateral reserved for unresolved orders"
            )
        ledger.position = replace(position, isolated_margin=isolated_margin_after)
        ledger.wallet_balance = updated_wallet
        if amount < 0:
            ledger.funding_paid += -amount
        else:
            ledger.funding_received += amount
        inserted = await self._repository.append_entry(
            PerpetualLedgerEntry(
                id=uuid4(),
                bot_id=bot_id,
                occurred_at=occurred_at,
                kind=PerpetualLedgerEventKind.FUNDING_SETTLED,
                wallet_delta=wallet_delta,
                isolated_margin_delta=margin_delta,
                funding=amount,
                quantity=position.quantity,
                side=position.side,
                price=ledger.mark_price,
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
