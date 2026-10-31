from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from fakes import fake_registry
from modules.exchanges.errors import RateLimited
from modules.market_data.application.updater import CandleUpdater, Series, UpdaterConfig
from modules.market_data.domain.models import Candle, MarketInfo, Timeframe, find_gaps

T0 = datetime(2024, 1, 1, tzinfo=UTC)
TF = Timeframe.M1
SERIES = Series("binance", "TST/USDT", TF)
CONFIG = UpdaterConfig(
    interval=timedelta(seconds=30),
    grace=timedelta(seconds=5),
    discover_every=timedelta(minutes=10),
    max_age=timedelta(days=7),
    stale_after_candles=3,
)


def candle(minute: int) -> Candle:
    price = Decimal(100 + minute)
    return Candle("TST/USDT", TF, T0 + timedelta(minutes=minute), price, price, price, price, price)


class FakeClock:
    def __init__(self, now: datetime) -> None:
        self.current = now

    def now(self) -> datetime:
        return self.current

    def advance(self, **kwargs: float) -> None:
        self.current += timedelta(**kwargs)


class FakeCandles:
    def __init__(self, opens: Sequence[int]) -> None:
        self.times = {T0 + timedelta(minutes=m) for m in opens}

    async def upsert_many(self, exchange: str, candles: Sequence[Candle]) -> int:
        self.times.update(c.open_time for c in candles)
        return len(candles)

    async def last_open_time(self, exchange: str, symbol: str, timeframe: Timeframe) -> Any:
        return max(self.times, default=None)

    async def list_series(self, last_after: datetime) -> list[tuple[str, str, Timeframe, datetime]]:
        last = max(self.times, default=None)
        if last is None or last < last_after:
            return []
        return [("binance", "TST/USDT", TF, last)]

    async def open_times(
        self, exchange: str, symbol: str, timeframe: Timeframe, start: datetime, end: datetime
    ) -> list[datetime]:
        return sorted(t for t in self.times if start <= t < end)


class FakeSource:
    """Serves every minute up to now, the in-progress one included, like an exchange does."""

    def __init__(self, clock: FakeClock) -> None:
        self.clock = clock
        self.calls: list[datetime] = []
        self.error: Exception | None = None

    async def fetch_candles(
        self, symbol: str, timeframe: Timeframe, since: datetime, limit: int
    ) -> list[Candle]:
        self.calls.append(since)
        if self.error is not None:
            raise self.error
        out: list[Candle] = []
        t = since
        while len(out) < limit and t <= self.clock.now():
            out.append(candle(int((t - T0).total_seconds() // 60)))
            t += TF.delta
        return out

    async def fetch_market_info(self, symbol: str) -> MarketInfo:
        raise NotImplementedError


class Env:
    def __init__(
        self, opens: Sequence[int], now: datetime, followed: set[Series] | None = None
    ) -> None:
        self.clock = FakeClock(now)
        self.candles = FakeCandles(opens)
        self.source = FakeSource(self.clock)
        self.updater = CandleUpdater(
            self._stores, fake_registry(self.source), self.clock, self._followed, CONFIG
        )
        self._set = followed or set()

    @asynccontextmanager
    async def _stores(self) -> AsyncIterator["Env"]:
        yield self

    async def commit(self) -> None:
        return None

    async def _followed(self) -> set[Series]:
        return self._set

    @property
    def last_minute(self) -> int:
        return int((max(self.candles.times) - T0).total_seconds() // 60)


async def test_extends_the_series_with_closed_candles_only() -> None:
    env = Env(range(10), T0 + timedelta(minutes=20, seconds=30))
    assert await env.updater.run_if_due() == 10  # minutes 10..19; minute 20 is still open
    assert env.last_minute == 19


async def test_a_second_pass_does_not_rewrite_or_request_anything() -> None:
    env = Env(range(10), T0 + timedelta(minutes=20, seconds=30))
    await env.updater.run_if_due()
    env.clock.advance(seconds=30)
    calls = len(env.source.calls)
    assert await env.updater.run_if_due() == 0
    assert len(env.source.calls) == calls


async def test_a_new_candle_is_picked_up_once_it_has_closed_plus_the_grace() -> None:
    env = Env(range(10), T0 + timedelta(minutes=20, seconds=30))
    await env.updater.run_if_due()
    env.clock.advance(seconds=30)  # minute 20 closes at 21:00 -> still inside the grace
    env.clock.current = T0 + timedelta(minutes=21, seconds=3)
    assert await env.updater.run_if_due() == 0
    env.clock.current = T0 + timedelta(minutes=21, seconds=35)
    assert await env.updater.run_if_due() == 1
    assert env.last_minute == 20


async def test_it_waits_for_the_interval_between_passes() -> None:
    env = Env(range(10), T0 + timedelta(minutes=20, seconds=30))
    await env.updater.run_if_due()
    calls = len(env.source.calls)
    env.clock.advance(seconds=10)
    await env.updater.run_if_due()
    assert len(env.source.calls) == calls


async def test_a_rate_limit_pauses_the_exchange_for_the_retry_after_the_exchange_gave() -> None:
    env = Env(range(10), T0 + timedelta(minutes=20, seconds=30))
    env.source.error = RateLimited("429", retry_after_seconds=90)
    assert await env.updater.run_if_due() == 0
    assert [p.exchange for p in env.updater.report().rate_limited] == ["binance"]
    env.source.error = None
    calls = len(env.source.calls)
    env.clock.advance(seconds=60)
    await env.updater.run_if_due()
    assert len(env.source.calls) == calls  # still inside Retry-After: nothing is sent
    env.clock.advance(seconds=40)
    assert await env.updater.run_if_due() > 0
    assert env.updater.report().rate_limited == ()


async def test_other_failures_back_off_and_never_raise() -> None:
    env = Env(range(10), T0 + timedelta(minutes=20, seconds=30))
    env.source.error = ConnectionError("down")
    assert await env.updater.run_if_due() == 0
    calls = len(env.source.calls)
    env.clock.advance(seconds=30)
    await env.updater.run_if_due()
    assert len(env.source.calls) == calls  # backed off for a minute
    env.clock.advance(seconds=31)
    await env.updater.run_if_due()
    assert len(env.source.calls) == calls + 1


async def test_a_gap_in_the_recent_window_is_refetched() -> None:
    env = Env([*range(0, 5), *range(8, 12)], T0 + timedelta(minutes=12, seconds=30))
    await env.updater.run_if_due()
    times = await env.candles.open_times("binance", "TST/USDT", TF, T0, T0 + timedelta(hours=1))
    assert find_gaps(times, TF) == []


async def test_an_abandoned_series_is_left_alone_unless_a_bot_follows_it() -> None:
    old = T0 + timedelta(days=30)
    env = Env(range(10), old)
    assert await env.updater.run_if_due() == 0
    assert env.source.calls == []
    followed = Env(range(10), old, {SERIES})
    assert await followed.updater.run_if_due() > 0


async def test_report_flags_a_series_that_fell_behind() -> None:
    env = Env(range(10), T0 + timedelta(minutes=20, seconds=30))
    env.source.error = ConnectionError("down")
    await env.updater.run_if_due()
    (stale,) = env.updater.report().stale
    assert stale.series == SERIES and stale.missing_candles == 10
