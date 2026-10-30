from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from factories import MARKET, T0
from modules.execution.domain.normalizer import OrderRejected, normalize_quantity
from modules.market_data.domain.models import Timeframe, find_gaps, floor_to_timeframe


def _times(offsets: list[int]) -> list[datetime]:
    return [T0 + timedelta(hours=h) for h in offsets]


def test_find_gaps_reports_missing_candles() -> None:
    gaps = find_gaps(_times([0, 1, 2, 5, 6, 8]), Timeframe.H1)
    assert [(g.start, g.end, g.missing) for g in gaps] == [
        (T0 + timedelta(hours=3), T0 + timedelta(hours=4), 2),
        (T0 + timedelta(hours=7), T0 + timedelta(hours=7), 1),
    ]


def test_find_gaps_on_contiguous_or_tiny_series() -> None:
    assert find_gaps(_times([0, 1, 2, 3]), Timeframe.H1) == []
    assert find_gaps(_times([0]), Timeframe.H1) == []
    assert find_gaps([], Timeframe.H1) == []


def test_floor_to_timeframe_aligns_to_utc_epoch() -> None:
    moment = datetime(2024, 3, 5, 13, 47, 12, tzinfo=UTC)
    assert floor_to_timeframe(moment, Timeframe.H1) == datetime(2024, 3, 5, 13, tzinfo=UTC)
    assert floor_to_timeframe(moment, Timeframe.H4) == datetime(2024, 3, 5, 12, tzinfo=UTC)
    assert floor_to_timeframe(moment, Timeframe.D1) == datetime(2024, 3, 5, tzinfo=UTC)
    with pytest.raises(ValueError):
        floor_to_timeframe(datetime(2024, 1, 1), Timeframe.H1)


def test_normalizer_rounds_quantity_down_to_lot_size() -> None:
    assert normalize_quantity(Decimal("0.123987"), Decimal(50_000), MARKET) == Decimal("0.123")


def test_normalizer_rejects_below_min_quantity_and_min_notional() -> None:
    with pytest.raises(OrderRejected, match="minimum quantity"):
        normalize_quantity(Decimal("0.0009"), Decimal(50_000), MARKET)
    with pytest.raises(OrderRejected, match="minimum"):
        normalize_quantity(Decimal("0.001"), Decimal(5_000), MARKET)  # notional 5 < 10
