"""Decimal helpers. Monetary values and quantities never use ``float``."""

from decimal import ROUND_DOWN, Decimal

from lost_crypto.core.errors import InvalidAmountError


def to_decimal(value: Decimal | int | str) -> Decimal:
    """Convert to a finite Decimal. ``float`` is rejected on purpose (precision loss)."""
    if isinstance(value, float):
        raise InvalidAmountError("float is not allowed for monetary values; use str or Decimal")
    try:
        result = value if isinstance(value, Decimal) else Decimal(value)
    except Exception as exc:  # decimal.InvalidOperation, TypeError
        raise InvalidAmountError(f"invalid decimal value: {value!r}") from exc
    if not result.is_finite():
        raise InvalidAmountError(f"non-finite decimal value: {value!r}")
    return result


def round_down_to_step(value: Decimal, step: Decimal) -> Decimal:
    """Round ``value`` down to a multiple of ``step`` (lot size / tick size)."""
    if step <= 0:
        raise InvalidAmountError("step must be positive")
    return (value / step).to_integral_value(rounding=ROUND_DOWN) * step
