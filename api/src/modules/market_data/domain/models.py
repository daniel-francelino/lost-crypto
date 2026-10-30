from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from itertools import pairwise


class Timeframe(StrEnum):
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"

    @property
    def delta(self) -> timedelta:
        return _DELTAS[self]


_DELTAS = {
    Timeframe.M1: timedelta(minutes=1),
    Timeframe.M5: timedelta(minutes=5),
    Timeframe.M15: timedelta(minutes=15),
    Timeframe.H1: timedelta(hours=1),
    Timeframe.H4: timedelta(hours=4),
    Timeframe.D1: timedelta(days=1),
}


@dataclass(frozen=True, slots=True)
class Candle:
    """A *closed* OHLCV candle. ``open_time`` is timezone-aware UTC."""

    symbol: str
    timeframe: Timeframe
    open_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal

    @property
    def close_time(self) -> datetime:
        return self.open_time + self.timeframe.delta


@dataclass(frozen=True, slots=True)
class MarketInfo:
    """Exchange trading rules for a symbol (used to normalise orders)."""

    symbol: str
    step_size: Decimal  # quantity increment (lot size)
    tick_size: Decimal  # price increment
    min_quantity: Decimal
    min_notional: Decimal


@dataclass(frozen=True, slots=True)
class Gap:
    start: datetime  # first missing candle open_time
    end: datetime  # last missing candle open_time
    missing: int


def floor_to_timeframe(moment: datetime, timeframe: Timeframe) -> datetime:
    """Start of the candle containing ``moment`` (exchange candles align to the UTC epoch)."""
    if moment.tzinfo is None:
        raise ValueError("naive datetime not allowed; use timezone-aware UTC")
    step = int(timeframe.delta.total_seconds())
    seconds = int(moment.timestamp())
    return datetime.fromtimestamp(seconds - seconds % step, UTC)


def find_gaps(open_times: Sequence[datetime], timeframe: Timeframe) -> list[Gap]:
    """Detect missing candles in a sorted sequence of candle open times."""
    delta = timeframe.delta
    gaps: list[Gap] = []
    for previous, current in pairwise(open_times):
        missing = (current - previous) // delta - 1
        if missing > 0:
            gaps.append(Gap(start=previous + delta, end=current - delta, missing=missing))
    return gaps
