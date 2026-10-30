from decimal import Decimal

import pytest

from lost_crypto.core.errors import InvalidAmountError
from lost_crypto.core.money import round_down_to_step, to_decimal


def test_to_decimal_accepts_str_int_and_decimal() -> None:
    assert to_decimal("0.1") == Decimal("0.1")
    assert to_decimal(5) == Decimal(5)
    assert to_decimal(Decimal("1.5")) == Decimal("1.5")


def test_to_decimal_rejects_float() -> None:
    with pytest.raises(InvalidAmountError):
        to_decimal(0.1)  # type: ignore[arg-type]


@pytest.mark.parametrize("bad", ["abc", "NaN", "Infinity"])
def test_to_decimal_rejects_invalid_and_non_finite(bad: str) -> None:
    with pytest.raises(InvalidAmountError):
        to_decimal(bad)


def test_round_down_to_step() -> None:
    assert round_down_to_step(Decimal("0.123456"), Decimal("0.001")) == Decimal("0.123")
    assert round_down_to_step(Decimal("10"), Decimal("0.5")) == Decimal("10.0")


def test_round_down_to_step_requires_positive_step() -> None:
    with pytest.raises(InvalidAmountError):
        round_down_to_step(Decimal("1"), Decimal("0"))
