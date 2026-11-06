"""Trend detector: only closed bars are fetched and classified, once, and the state resumes."""

import math
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest

from core.errors import ConflictError, NotFoundError
from fakes import fake_registry
from modules.exchanges.errors import RateLimited, UnknownSymbolError
from modules.market_data.domain.models import Candle, MarketInfo, Timeframe
from modules.market_data.domain.trend import (
    DEFAULT_SETTINGS,
    FrameTrend,
    Trend,
    TrendFrame,
    TrendSettings,
    build_bars,
    frame_floor,
)
from modules.trends.application.detector import DetectorConfig, TrendDetector
from modules.trends.application.service import InvalidTrendSymbol, TrendService
from modules.trends.domain.models import (
    FrameProgress,
    TrendRecord,
    WatchedSymbol,
    normalize_symbol,
)

EXCHANGE = "binance"
SYMBOL = "TST/USDT"
EPOCH = datetime(2020, 1, 6, tzinfo=UTC)  # a Monday
# A Monday 10:00:30 UTC: the 1h bar of 09:00 closed 30 s ago, the 4h bar of 08:00 is open.
NOW = datetime(2024, 6, 3, 10, 0, 30, tzinfo=UTC)
CONFIG = DetectorConfig(warmup_bars=60)


class FakeClock:
    def __init__(self, now: datetime) -> None:
        self.current = now

    def now(self) -> datetime:
        return self.current

    def advance(self, **kwargs: float) -> None:
        self.current += timedelta(**kwargs)


def _price(moment: datetime) -> Decimal:
    hours = (moment - EPOCH).total_seconds() / 3600
    return Decimal(f"{100 + 0.05 * hours + 30 * math.sin(2 * math.pi * hours / (24 * 12)):.4f}")


def _candle(timeframe: Timeframe, open_time: datetime) -> Candle:
    opened, closed = _price(open_time), _price(open_time + timeframe.delta)
    return Candle(
        SYMBOL,
        timeframe,
        open_time,
        opened,
        max(opened, closed) + Decimal("0.5"),
        min(opened, closed) - Decimal("0.5"),
        closed,
        Decimal(1),
    )


class FakeSource:
    """An exchange: every candle up to now, the in-progress one included."""

    def __init__(self, clock: FakeClock) -> None:
        self.clock = clock
        self.calls: list[tuple[Timeframe, datetime]] = []
        self.error: Exception | None = None

    async def fetch_candles(
        self, symbol: str, timeframe: Timeframe, since: datetime, limit: int
    ) -> list[Candle]:
        self.calls.append((timeframe, since))
        if self.error is not None:
            raise self.error
        out: list[Candle] = []
        t = since
        while len(out) < limit and t <= self.clock.now():
            out.append(_candle(timeframe, t))
            t += timeframe.delta
        return out

    async def fetch_market_info(self, symbol: str) -> MarketInfo:
        if symbol.startswith("NOPE"):
            raise UnknownSymbolError(symbol)
        return MarketInfo(symbol, Decimal("0.001"), Decimal("0.01"), Decimal("0.001"), Decimal(10))


class FakeCandles:
    def __init__(self) -> None:
        self.rows: dict[tuple[str, str, Timeframe], dict[datetime, Candle]] = {}

    def _series(self, exchange: str, symbol: str, timeframe: Timeframe) -> dict[datetime, Candle]:
        return self.rows.setdefault((exchange, symbol, timeframe), {})

    async def bounds(
        self, exchange: str, symbol: str, timeframe: Timeframe
    ) -> tuple[int, datetime | None, datetime | None]:
        rows = self._series(exchange, symbol, timeframe)
        return len(rows), min(rows, default=None), max(rows, default=None)

    async def upsert_many(self, exchange: str, candles: Sequence[Candle]) -> int:
        for c in candles:
            self._series(exchange, c.symbol, c.timeframe)[c.open_time] = c
        return len(candles)

    async def get_range(
        self, exchange: str, symbol: str, timeframe: Timeframe, start: datetime, end: datetime
    ) -> list[Candle]:
        rows = self._series(exchange, symbol, timeframe)
        return [rows[t] for t in sorted(rows) if start <= t < end]


class FakeTrends:
    def __init__(self) -> None:
        self.symbols: dict[UUID, WatchedSymbol] = {}
        self.progress: dict[tuple[str, str, TrendFrame], FrameProgress] = {}
        self.records: dict[tuple[str, str, TrendFrame, datetime], TrendRecord] = {}

    async def list_symbols(self, *, active_only: bool) -> list[WatchedSymbol]:
        return [s for s in self.symbols.values() if s.active or not active_only]

    async def get_symbol(self, symbol_id: UUID) -> WatchedSymbol | None:
        return self.symbols.get(symbol_id)

    async def find_symbol(self, exchange: str, symbol: str) -> WatchedSymbol | None:
        return next(
            (s for s in self.symbols.values() if (s.exchange, s.symbol) == (exchange, symbol)), None
        )

    async def add_symbol(self, symbol: WatchedSymbol) -> None:
        self.symbols[symbol.id] = symbol

    async def set_active(self, symbol_id: UUID, active: bool) -> bool:
        found = self.symbols.get(symbol_id)
        if found is None:
            return False
        self.symbols[symbol_id] = WatchedSymbol(
            found.id, found.exchange, found.symbol, active, found.created_at
        )
        return True

    async def get_progress(self, exchange: str, symbol: str) -> dict[TrendFrame, FrameProgress]:
        return {f: p for (e, s, f), p in self.progress.items() if (e, s) == (exchange, symbol)}

    async def save_progress(
        self, exchange: str, symbol: str, progress: FrameProgress, now: datetime
    ) -> None:
        self.progress[(exchange, symbol, progress.frame)] = progress

    async def reset_frame(self, exchange: str, symbol: str, frame: TrendFrame) -> None:
        self.progress.pop((exchange, symbol, frame), None)
        for key in [k for k in self.records if k[:3] == (exchange, symbol, frame)]:
            del self.records[key]

    async def upsert_records(self, records: Sequence[TrendRecord]) -> int:
        for r in records:
            self.records[(r.exchange, r.symbol, r.frame, r.bar_open_time)] = r
        return len(records)

    async def latest(self, exchange: str, symbol: str) -> list[TrendRecord]:
        out = []
        for frame in TrendFrame:
            rows = [r for k, r in self.records.items() if k[:3] == (exchange, symbol, frame)]
            if rows:
                out.append(max(rows, key=lambda r: r.bar_open_time))
        return out

    async def history(
        self, exchange: str, symbol: str, frame: TrendFrame, limit: int, before: Any = None
    ) -> list[TrendRecord]:
        rows = [r for k, r in self.records.items() if k[:3] == (exchange, symbol, frame)]
        rows = [r for r in rows if before is None or r.bar_open_time < before]
        return sorted(rows, key=lambda r: r.bar_open_time, reverse=True)[:limit]


class Env:
    def __init__(self, config: DetectorConfig = CONFIG, now: datetime = NOW) -> None:
        self.clock = FakeClock(now)
        self.source = FakeSource(self.clock)
        self.candles = FakeCandles()
        self.trends = FakeTrends()
        self.registry = fake_registry(self.source)
        self.detector = TrendDetector(self._stores, self.registry, self.clock, config)  # type: ignore[arg-type]
        self.service = TrendService(self._stores, self.registry, self.clock, _Ids())  # type: ignore[arg-type]

    @asynccontextmanager
    async def _stores(self) -> AsyncIterator["Env"]:
        yield self

    async def commit(self) -> None:
        return None

    def follow(self, symbol: str = SYMBOL, active: bool = True) -> WatchedSymbol:
        item = WatchedSymbol(uuid4(), EXCHANGE, symbol, active, self.clock.now())
        self.trends.symbols[item.id] = item
        return item

    def last_bar(self, frame: TrendFrame) -> datetime:
        return self.trends.progress[(EXCHANGE, SYMBOL, frame)].last_bar_open_time

    def calls(self, timeframe: Timeframe) -> int:
        return sum(1 for tf, _ in self.source.calls if tf is timeframe)


class _Ids:
    def new_id(self) -> UUID:
        return uuid4()


def _newest_closed(frame: TrendFrame, now: datetime, grace_seconds: int = 5) -> datetime:
    return frame_floor(frame, now - timedelta(seconds=grace_seconds)) - frame.delta


# --- what a pass does ---------------------------------------------------------------------------


async def test_the_first_pass_backfills_and_classifies_every_timeframe() -> None:
    env = Env()
    env.follow()

    written = await env.detector.run_if_due()

    assert written > 0
    for frame in TrendFrame:
        assert env.last_bar(frame) == _newest_closed(frame, NOW), frame
    latest = {r.frame: r for r in await env.trends.latest(EXCHANGE, SYMBOL)}
    assert set(latest) == set(TrendFrame)
    assert latest[TrendFrame.D1].trend is Trend.BULLISH  # a steady climb
    assert latest[TrendFrame.D1].confirmed in (True, False)
    assert latest[TrendFrame.H1].bar_open_time == NOW.replace(minute=0, second=0) - timedelta(
        hours=1
    )


async def test_no_request_is_made_while_no_bar_has_closed() -> None:
    env = Env()
    env.follow()
    await env.detector.run_if_due()
    env.source.calls.clear()

    env.clock.advance(minutes=20)  # 10:20: nothing new closed
    assert await env.detector.run_if_due() == 0
    assert env.source.calls == []


async def test_only_the_timeframes_whose_bar_closed_are_fetched() -> None:
    env = Env()
    env.follow()
    await env.detector.run_if_due()
    last_h1 = env.last_bar(TrendFrame.H1)
    env.source.calls.clear()

    env.clock.advance(hours=1)  # 11:00:30: the 10:00 hourly bar closed, the 4h bar did not
    assert await env.detector.run_if_due() == 1
    assert env.source.calls == [(Timeframe.H1, last_h1 + Timeframe.H1.delta)]
    assert env.last_bar(TrendFrame.H1) == last_h1 + timedelta(hours=1)

    env.source.calls.clear()
    env.clock.advance(hours=1)  # 12:00:30: the 08:00-12:00 bar closes too
    assert await env.detector.run_if_due() == 2
    assert {tf for tf, _ in env.source.calls} == {Timeframe.H1, Timeframe.H4}


async def test_only_missing_candles_are_requested() -> None:
    env = Env()
    env.follow()
    await env.detector.run_if_due()
    stored_h1 = (await env.candles.bounds(EXCHANGE, SYMBOL, Timeframe.H1))[2]
    assert stored_h1 is not None
    env.source.calls.clear()

    env.clock.advance(hours=1)
    await env.detector.run_if_due()
    ((timeframe, since),) = env.source.calls
    assert (timeframe, since) == (Timeframe.H1, stored_h1 + Timeframe.H1.delta)


async def test_the_week_closes_on_monday_and_costs_one_daily_request() -> None:
    sunday_evening = datetime(2024, 6, 2, 23, 0, 30, tzinfo=UTC)
    env = Env(now=sunday_evening)
    env.follow()
    await env.detector.run_if_due()
    last_week = env.last_bar(TrendFrame.W1)
    env.source.calls.clear()

    env.clock.advance(hours=1)  # Monday 00:00:30: hour, 4h, day and week all just closed
    await env.detector.run_if_due()

    assert env.last_bar(TrendFrame.W1) == last_week + timedelta(days=7)
    assert env.calls(Timeframe.D1) == 1  # the weekly bar reuses the daily candle just stored
    assert env.calls(Timeframe.H1) == 1 and env.calls(Timeframe.H4) == 1


async def test_a_frame_that_is_up_to_date_is_not_touched_again() -> None:
    env = Env()
    env.follow()
    await env.detector.run_if_due()
    records = dict(env.trends.records)
    env.clock.advance(seconds=61)
    env.source.calls.clear()

    assert await env.detector.run_if_due() == 0
    assert env.source.calls == [] and env.trends.records == records


async def test_passes_are_throttled_by_the_interval() -> None:
    env = Env()
    env.follow()
    await env.detector.run_if_due()
    env.clock.advance(hours=1)
    env.clock.current -= timedelta(minutes=59)  # still inside the 60 s interval of the last pass
    env.clock.advance(seconds=30)
    assert await env.detector.run_if_due() == 0


async def test_resuming_from_the_stored_state_equals_one_straight_run() -> None:
    env = Env()
    env.follow()
    await env.detector.run_if_due()
    for _ in range(5):
        env.clock.advance(hours=1)
        await env.detector.run_if_due()

    stored = {r.bar_open_time: r for k, r in env.trends.records.items() if k[2] is TrendFrame.H1}
    engine = FrameTrend(TrendFrame.H1, DEFAULT_SETTINGS[TrendFrame.H1])
    state = engine.initial_state()
    candles = await env.candles.get_range(EXCHANGE, SYMBOL, Timeframe.H1, EPOCH, env.clock.now())
    for bar in build_bars(candles, TrendFrame.H1):
        state = engine.update(state, bar)
        reading = engine.read(state)
        if reading.trend is not None and bar.open_time in stored:
            assert stored[bar.open_time].ema_fast == reading.ema_fast
            assert stored[bar.open_time].trend is reading.trend


async def test_changing_the_ema_lengths_restarts_the_frame() -> None:
    env = Env()
    env.follow()
    await env.detector.run_if_due()
    before = env.trends.progress[(EXCHANGE, SYMBOL, TrendFrame.D1)]

    settings = dict(DEFAULT_SETTINGS)
    settings[TrendFrame.D1] = TrendSettings(fast=10, slow=30, adx_period=14)
    env.detector = TrendDetector(
        env._stores,  # type: ignore[arg-type]
        env.registry,
        env.clock,
        DetectorConfig(warmup_bars=60, settings=settings),
    )
    env.clock.advance(seconds=61)
    await env.detector.run_if_due()

    after = env.trends.progress[(EXCHANGE, SYMBOL, TrendFrame.D1)]
    assert after.settings_key != before.settings_key == "20/50/1.5/25/14/5/2"
    assert after.settings_key.startswith("10/30/")


async def test_inactive_symbols_are_ignored() -> None:
    env = Env()
    env.follow(active=False)
    assert await env.detector.run_if_due() == 0 and env.source.calls == []


async def test_an_old_hole_in_the_stored_history_does_not_block_a_new_frame() -> None:
    env = Env()
    env.follow()
    hole_start = NOW - timedelta(hours=40)
    for h in range(0, 100):
        t = hole_start - timedelta(hours=100 - h)
        if h in (10, 11, 12):
            continue
        await env.candles.upsert_many(EXCHANGE, [_candle(Timeframe.H1, t)])
    await env.detector.run_if_due()
    assert (EXCHANGE, SYMBOL, TrendFrame.H1) in env.trends.progress


# --- failures -----------------------------------------------------------------------------------


async def test_a_rate_limit_pauses_the_exchange_until_it_may_be_used_again() -> None:
    env = Env()
    env.follow()
    env.source.error = RateLimited("slow down", retry_after_seconds=120)
    assert await env.detector.run_if_due() == 0
    assert len(env.source.calls) == 1  # it stopped at the first 429

    env.source.error = None
    env.source.calls.clear()
    env.clock.advance(seconds=70)
    await env.detector.run_if_due()
    assert env.source.calls == []  # still inside the Retry-After

    env.clock.advance(seconds=60)
    assert await env.detector.run_if_due() > 0


async def test_an_unknown_symbol_is_parked_for_an_hour() -> None:
    env = Env()
    env.follow()
    env.source.error = UnknownSymbolError(SYMBOL)
    await env.detector.run_if_due()
    env.source.error = None
    env.source.calls.clear()
    env.clock.advance(minutes=30)
    await env.detector.run_if_due()
    assert env.source.calls == []
    env.clock.advance(minutes=40)
    assert await env.detector.run_if_due() > 0


async def test_a_failing_symbol_does_not_stop_the_others() -> None:
    env = Env()
    env.follow("BAD/USDT")
    env.follow(SYMBOL)

    original = env.source.fetch_candles

    async def fetch(symbol: str, timeframe: Timeframe, since: datetime, limit: int) -> list[Candle]:
        if symbol == "BAD/USDT":
            raise ValueError("boom")
        return await original(symbol, timeframe, since, limit)

    env.source.fetch_candles = fetch  # type: ignore[method-assign]
    assert await env.detector.run_if_due() > 0
    assert (EXCHANGE, SYMBOL, TrendFrame.D1) in env.trends.progress


def test_warmup_must_cover_what_the_indicators_need() -> None:
    with pytest.raises(ValueError):
        DetectorConfig(warmup_bars=40)


# --- the symbol registry --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("exchange", "text", "expected"),
    [
        ("binance-usdm", "btcusdt", "BTC/USDT:USDT"),
        ("binance", "SOLUSDT", "SOL/USDT"),
        ("binance-usdm", "BTC/USDT:USDT", "BTC/USDT:USDT"),
        ("binance", " eth/usdt ", "ETH/USDT"),
    ],
)
def test_symbols_are_normalised(exchange: str, text: str, expected: str) -> None:
    assert normalize_symbol(exchange, text) == expected


async def test_registering_a_symbol_validates_it_and_rejects_duplicates() -> None:
    env = Env()
    added = await env.service.add_symbol(EXCHANGE, "ethusdt")
    assert (added.exchange, added.symbol, added.active) == (EXCHANGE, "ETH/USDT", True)

    with pytest.raises(ConflictError):
        await env.service.add_symbol(EXCHANGE, "ETH/USDT")
    with pytest.raises(InvalidTrendSymbol):
        await env.service.add_symbol(EXCHANGE, "NOPE/USDT")


async def test_a_deactivated_symbol_can_be_switched_back_on() -> None:
    env = Env()
    added = await env.service.add_symbol(EXCHANGE, "ETH/USDT")
    assert (await env.service.set_active(added.id, False)).active is False
    again = await env.service.add_symbol(EXCHANGE, "ETH/USDT")
    assert again.id == added.id and again.active is True
    with pytest.raises(NotFoundError):
        await env.service.set_active(uuid4(), True)


async def test_the_service_reads_what_the_detector_stored() -> None:
    env = Env()
    env.follow()
    await env.detector.run_if_due()

    (item,) = await env.service.latest()
    assert {r.frame for r in item.readings} == set(TrendFrame)
    (only,) = await env.service.latest(EXCHANGE, SYMBOL)
    assert only.symbol.symbol == SYMBOL

    history = await env.service.history(EXCHANGE, SYMBOL, TrendFrame.H1, limit=5)
    assert len(history) == 5
    assert history[0].bar_open_time > history[-1].bar_open_time  # newest first
    older = await env.service.history(
        EXCHANGE, SYMBOL, TrendFrame.H1, limit=5, before=history[-1].bar_open_time
    )
    assert older and older[0].bar_open_time < history[-1].bar_open_time
