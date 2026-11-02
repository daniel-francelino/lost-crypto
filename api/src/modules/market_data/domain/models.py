from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from itertools import pairwise
from uuid import UUID


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
class RegimeBreak:
    """A date the operator named as a structural break (book 2 ch. 5). ``exchange`` and
    ``symbol`` are None for a break that applies to every market."""

    id: UUID
    name: str
    occurred_at: datetime
    exchange: str | None
    symbol: str | None
    note: str | None
    created_by: str
    created_at: datetime


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
class MarkPrice:
    symbol: str
    price: Decimal
    timestamp: datetime
    source: str = "exchange_mark_price"

    def __post_init__(self) -> None:
        if self.price <= 0 or self.timestamp.tzinfo is None:
            raise ValueError("mark price must be positive and timestamp timezone-aware")


@dataclass(frozen=True, slots=True)
class FundingRate:
    symbol: str
    rate: Decimal
    funding_time: datetime
    mark_price: Decimal | None = None
    rate_type: str = "regular"

    def __post_init__(self) -> None:
        if self.funding_time.tzinfo is None:
            raise ValueError("funding time must be timezone-aware")
        if self.mark_price is not None and self.mark_price <= 0:
            raise ValueError("funding mark price must be positive when present")
        if self.rate_type not in {"regular", "special"}:
            raise ValueError("funding rate type must be regular or special")


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


def ceil_to_timeframe(moment: datetime, timeframe: Timeframe) -> datetime:
    floored = floor_to_timeframe(moment, timeframe)
    return floored if floored == moment else floored + timeframe.delta


@dataclass(frozen=True, slots=True)
class RangeCoverage:
    """Expected vs present candles in ``[start, end)``, gaps at the edges included."""

    expected: int
    present: int
    gaps: list[Gap]

    @property
    def missing(self) -> int:
        return self.expected - self.present

    @property
    def largest_gap(self) -> int:
        return max((g.missing for g in self.gaps), default=0)


def range_coverage(
    open_times: Sequence[datetime],
    timeframe: Timeframe,
    start: datetime,
    end: datetime,
    now: datetime,
) -> RangeCoverage:
    """Gaps of a series inside a requested range; only candles closed by ``now`` are expected."""
    delta = timeframe.delta
    first = ceil_to_timeframe(start, timeframe)
    stop = min(end, floor_to_timeframe(now, timeframe))
    if stop <= first:
        return RangeCoverage(0, 0, [])
    expected = -(-(stop - first) // delta)
    inside = [t for t in open_times if first <= t < stop]
    sentinels = [first - delta, *inside, first + expected * delta]
    return RangeCoverage(expected, len(inside), find_gaps(sentinels, timeframe))


@dataclass(frozen=True, slots=True)
class ListedMarket:
    symbol: str
    active: bool  # listed but halted (e.g. Binance "BREAK") is inactive
    product: str = "spot"
    base: str | None = None
    quote: str | None = None
    settlement: str | None = None
    contract_size: Decimal = Decimal(1)


@dataclass(frozen=True, slots=True)
class Listing:
    exchange: str
    symbol: str
    status: str  # "active" | "inactive" | "delisted"
    first_seen: datetime
    last_seen: datetime
    delisted_at: datetime | None
