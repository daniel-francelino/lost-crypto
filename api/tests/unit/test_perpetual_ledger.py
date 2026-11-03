from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from modules.exchanges.domain.models import PositionSide
from modules.portfolio.application.perpetual_ledger_service import PerpetualLedgerService
from modules.portfolio.domain.perpetual_ledger import (
    PerpetualLedgerEntry,
    PerpetualLedgerEventKind,
)
from modules.portfolio.domain.perpetuals import (
    InvalidPerpetualPosition,
    PerpetualLedger,
)

D = Decimal


class _LedgerRepository:
    def __init__(self, ledger: PerpetualLedger) -> None:
        self.ledger = ledger
        self.entries: list[PerpetualLedgerEntry] = []
        self.saved = False

    async def get(self, bot_id: UUID) -> PerpetualLedger | None:
        return self.ledger if self.ledger.bot_id == bot_id else None

    async def has_entry(self, bot_id: UUID, external_reference: str) -> bool:
        return any(
            entry.bot_id == bot_id and entry.external_reference == external_reference
            for entry in self.entries
        )

    async def append_entry(self, entry: PerpetualLedgerEntry) -> bool:
        self.entries.append(entry)
        return True

    async def save(self, ledger: PerpetualLedger) -> None:
        self.ledger = ledger
        self.saved = True


def test_reservation_reduces_available_collateral_without_changing_equity() -> None:
    ledger = PerpetualLedger.new(uuid4(), D("1000"))

    ledger.reserve(D("200"))

    assert ledger.available_balance == D("800")
    assert ledger.equity(D("100")) == D("1000")
    ledger.release(D("200"))
    assert ledger.available_balance == D("1000")


def test_partial_close_releases_only_pro_rata_margin_and_realizes_signed_pnl() -> None:
    ledger = PerpetualLedger.new(uuid4(), D("1000"))
    ledger.open_position(
        PositionSide.LONG,
        D("2"),
        D("100"),
        leverage=2,
        fee=D("1"),
        stop_price=D("90"),
        take_profit_price=D("120"),
    )
    ledger.reserve(D("100"))

    realized = ledger.close_position(D("1"), D("110"), fee=D("0.5"))

    assert realized == D("9.5")
    assert ledger.position is not None
    assert ledger.position.quantity == D("1")
    assert ledger.position.isolated_margin == D("50")
    assert ledger.position.stop_price == D("90")
    assert ledger.wallet_balance == D("958.5")
    assert ledger.available_balance == D("858.5")
    assert ledger.equity(D("110")) == D("1018.5")


@pytest.mark.parametrize(
    ("side", "rate", "paid", "received"),
    [
        (PositionSide.LONG, D("0.01"), D("2"), D("0")),
        (PositionSide.SHORT, D("0.01"), D("0"), D("2")),
    ],
)
def test_funding_uses_mark_not_entry_and_follows_position_side(
    side: PositionSide, rate: Decimal, paid: Decimal, received: Decimal
) -> None:
    ledger = PerpetualLedger.new(uuid4(), D("1000"))
    ledger.open_position(side, D("1"), D("100"), leverage=2)

    amount = ledger.apply_funding(D("200"), rate)

    assert amount == (D("-2") if side is PositionSide.LONG else D("2"))
    assert ledger.funding_paid == paid
    assert ledger.funding_received == received
    assert ledger.position is not None and ledger.position.isolated_margin == D("50")
    assert ledger.wallet_balance == (D("948") if side is PositionSide.LONG else D("952"))


def test_funding_uses_available_wallet_before_isolated_position_margin() -> None:
    ledger = PerpetualLedger.new(uuid4(), D("1000"))
    ledger.open_position(PositionSide.LONG, D("1"), D("100"), leverage=2)
    ledger.reserve(D("949"))

    payment = ledger.apply_funding(D("100"), D("0.02"))

    assert payment == D("-2")
    assert ledger.wallet_balance == D("949")
    assert ledger.reserved_margin == D("949")
    assert ledger.position is not None and ledger.position.isolated_margin == D("49")
    assert ledger.funding_paid == D("2")


def test_funding_cannot_spend_reserved_collateral_or_make_wallet_negative() -> None:
    ledger = PerpetualLedger.new(uuid4(), D("1000"))
    ledger.open_position(PositionSide.LONG, D("1"), D("100"), leverage=2)
    ledger.reserve(D("950"))

    payment = ledger.apply_funding(D("100"), D("0.6"))

    assert payment == D("-50")  # only the isolated margin can settle the remaining charge
    assert ledger.funding_paid == D("50")
    assert ledger.wallet_balance == D("950")
    assert ledger.reserved_margin == D("950")
    assert ledger.available_balance == 0
    assert ledger.position is None
    assert ledger.realized_pnl == D("-50")


@pytest.mark.asyncio
async def test_funding_liquidation_persists_cash_margin_and_realized_deltas() -> None:
    bot_id = uuid4()
    ledger = PerpetualLedger.new(bot_id, D("100"))
    ledger.open_position(PositionSide.LONG, D("1"), D("100"), leverage=2)
    repository = _LedgerRepository(ledger)
    service = PerpetualLedgerService(repository)

    settled = await service.settle_funding(
        bot_id,
        mark_price=D("100"),
        funding_rate=D("1.1"),
        occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
        external_reference="funding:BTC:2026-01-01T00:00:00+00:00:regular",
    )

    assert settled and repository.saved
    assert len(repository.entries) == 1
    entry = repository.entries[0]
    assert entry.kind is PerpetualLedgerEventKind.LIQUIDATED
    assert entry.wallet_delta == D("-50")
    assert entry.isolated_margin_delta == D("-50")
    assert entry.realized_pnl_delta == D("-50")
    assert entry.funding == D("-100")
    assert repository.ledger.wallet_balance == 0
    assert repository.ledger.position is None
    assert not await service.settle_funding(
        bot_id,
        mark_price=D("100"),
        funding_rate=D("1.1"),
        occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
        external_reference="funding:BTC:2026-01-01T00:00:00+00:00:regular",
    )
    assert len(repository.entries) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("amount", "margin_after", "wallet_delta", "margin_delta", "paid", "received"),
    [
        (D("-2"), D("48"), D("0"), D("-2"), D("2"), D("0")),
        (D("2"), D("50"), D("2"), D("0"), D("0"), D("2")),
    ],
)
async def test_exchange_funding_uses_actual_income_and_isolated_wallet_once(
    amount: Decimal,
    margin_after: Decimal,
    wallet_delta: Decimal,
    margin_delta: Decimal,
    paid: Decimal,
    received: Decimal,
) -> None:
    bot_id = uuid4()
    ledger = PerpetualLedger.new(bot_id, D("1000"))
    ledger.open_position(PositionSide.LONG, D("1"), D("100"), leverage=2)
    ledger.mark(D("100"), datetime(2026, 1, 1, tzinfo=UTC), D("0.005"))
    repository = _LedgerRepository(ledger)
    service = PerpetualLedgerService(repository)
    event_time = datetime(2026, 1, 1, 8, tzinfo=UTC)
    equity_before = ledger.equity(D("100"))

    applied = await service.settle_exchange_funding_income(
        bot_id,
        amount=amount,
        isolated_margin_after=margin_after,
        occurred_at=event_time,
        transaction_id="funding-tx-123",
    )

    assert applied and repository.saved
    entry = repository.entries[0]
    assert entry.external_reference == "binance:funding:funding-tx-123"
    assert entry.wallet_delta == wallet_delta
    assert entry.isolated_margin_delta == margin_delta
    assert entry.funding == amount
    assert repository.ledger.funding_paid == paid
    assert repository.ledger.funding_received == received
    assert repository.ledger.position is not None
    assert repository.ledger.position.isolated_margin == margin_after
    assert repository.ledger.equity(D("100")) == equity_before + amount

    duplicate = await service.settle_exchange_funding_income(
        bot_id,
        amount=amount,
        isolated_margin_after=margin_after,
        occurred_at=event_time,
        transaction_id="funding-tx-123",
    )
    assert not duplicate
    assert len(repository.entries) == 1


def test_partial_close_cannot_close_more_than_the_open_position() -> None:
    ledger = PerpetualLedger.new(uuid4(), D("1000"))
    ledger.open_position(PositionSide.SHORT, D("1"), D("100"), leverage=1)

    with pytest.raises(InvalidPerpetualPosition, match="within the open position"):
        ledger.close_position(D("1.01"), D("90"))


def test_position_rejects_leverage_above_system_cap() -> None:
    ledger = PerpetualLedger.new(uuid4(), D("10000"))

    with pytest.raises(InvalidPerpetualPosition, match="between 1x and 10x"):
        ledger.open_position(PositionSide.LONG, D("1"), D("100"), leverage=11)


def test_position_rejects_zero_leverage_before_margin_division() -> None:
    ledger = PerpetualLedger.new(uuid4(), D("10000"))

    with pytest.raises(InvalidPerpetualPosition, match="between 1x and 10x"):
        ledger.open_position(PositionSide.LONG, D("1"), D("100"), leverage=0)


def test_exchange_liquidation_metadata_is_cleared_when_position_is_reopened() -> None:
    ledger = PerpetualLedger.new(uuid4(), D("1000"))
    ledger.open_position(PositionSide.LONG, D("1"), D("100"), leverage=2)
    ledger.exchange_position_id = "BTCUSDT"
    ledger.exchange_liquidation_price = D("50")
    ledger.reconciled_at = datetime(2024, 1, 1, tzinfo=UTC)

    ledger.close_position(D("1"), D("100"))
    ledger.open_position(PositionSide.SHORT, D("1"), D("200"), leverage=2)

    assert ledger.exchange_position_id is None
    assert ledger.exchange_liquidation_price is None
    assert ledger.reconciled_at is None
