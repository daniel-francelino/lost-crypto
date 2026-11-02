"""Immutable records for the isolated USDT perpetual ledger."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from modules.exchanges.domain.models import PositionSide


class PerpetualLedgerEventKind(StrEnum):
    COLLATERAL_ADDED = "collateral_added"
    MARGIN_RESERVED = "margin_reserved"
    MARGIN_RELEASED = "margin_released"
    POSITION_OPENED = "position_opened"
    POSITION_INCREASED = "position_increased"
    POSITION_REDUCED = "position_reduced"
    FUNDING_SETTLED = "funding_settled"
    FEE_CHARGED = "fee_charged"
    LIQUIDATED = "liquidated"
    RECONCILED = "reconciled"


@dataclass(frozen=True, slots=True)
class PerpetualLedgerEntry:
    """One append-only balance or position change, idempotent by ``id``."""

    id: UUID
    bot_id: UUID
    occurred_at: datetime
    kind: PerpetualLedgerEventKind
    wallet_delta: Decimal = Decimal(0)
    isolated_margin_delta: Decimal = Decimal(0)
    reserved_margin_delta: Decimal = Decimal(0)
    realized_pnl_delta: Decimal = Decimal(0)
    fee: Decimal = Decimal(0)
    funding: Decimal = Decimal(0)  # positive = received, negative = paid
    quantity: Decimal | None = None
    side: PositionSide | None = None
    price: Decimal | None = None
    source: str = "internal"
    external_reference: str | None = None

    def __post_init__(self) -> None:
        if self.occurred_at.tzinfo is None:
            raise ValueError("perpetual ledger event time must be timezone-aware")
        if (
            self.kind is PerpetualLedgerEventKind.MARGIN_RESERVED
            and self.reserved_margin_delta <= 0
        ):
            raise ValueError("margin reservation events require a positive reserved delta")
        if (
            self.kind is PerpetualLedgerEventKind.MARGIN_RELEASED
            and self.reserved_margin_delta >= 0
        ):
            raise ValueError("margin release events require a negative reserved delta")
        if self.fee < 0 or (self.quantity is not None and self.quantity <= 0):
            raise ValueError("ledger fee or quantity is invalid")
        if self.price is not None and self.price <= 0:
            raise ValueError("ledger price must be positive")


@dataclass(frozen=True, slots=True)
class PerpetualPortfolioSnapshot:
    bot_id: UUID
    session_id: UUID
    taken_at: datetime
    mark_price: Decimal
    wallet_balance: Decimal
    isolated_margin: Decimal
    position_side: PositionSide | None
    quantity: Decimal
    entry_price: Decimal
    equity: Decimal
    unrealized_pnl: Decimal
    funding_paid: Decimal
    funding_received: Decimal
    mark_source: str = "exchange_mark_price"

    def __post_init__(self) -> None:
        if self.taken_at.tzinfo is None or self.mark_price <= 0:
            raise ValueError("snapshot requires a positive mark price and aware timestamp")
        if (
            min(
                self.wallet_balance,
                self.isolated_margin,
                self.quantity,
                self.entry_price,
                self.funding_paid,
                self.funding_received,
            )
            < 0
        ):
            raise ValueError("perpetual snapshot amounts cannot be negative")
        if (self.position_side is None) != (self.quantity == 0):
            raise ValueError("snapshot position side and quantity disagree")
