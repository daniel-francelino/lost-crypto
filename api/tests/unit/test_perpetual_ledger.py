from decimal import Decimal
from uuid import uuid4

import pytest

from modules.exchanges.domain.models import PositionSide
from modules.portfolio.domain.perpetuals import (
    InvalidPerpetualPosition,
    PerpetualLedger,
)

D = Decimal


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


def test_partial_close_cannot_close_more_than_the_open_position() -> None:
    ledger = PerpetualLedger.new(uuid4(), D("1000"))
    ledger.open_position(PositionSide.SHORT, D("1"), D("100"), leverage=1)

    with pytest.raises(InvalidPerpetualPosition, match="within the open position"):
        ledger.close_position(D("1.01"), D("90"))


def test_position_rejects_leverage_above_system_cap() -> None:
    ledger = PerpetualLedger.new(uuid4(), D("10000"))

    with pytest.raises(InvalidPerpetualPosition, match="between 1x and 10x"):
        ledger.open_position(PositionSide.LONG, D("1"), D("100"), leverage=11)
