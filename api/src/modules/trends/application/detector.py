"""The trend detector (worker side): scheduler step, candle synchronizer and classification.

Every pass (a cheap look at the clock and at what is stored) it takes the active symbols from
the registry and, for each timeframe, asks one question: *has a bar closed since the last one I
processed?* Only then does it work:

1. **Candle synchronizer.** Fetches from the exchange just the closed candles that are not in
   the database yet (one request when a candle closed, more only for a first backfill), in the
   timeframe being analysed: 1h, 4h and 1d candles come straight from the exchange, the weekly
   bar is built from the stored daily candles. Nothing is requested while no candle closed.
2. **Trend detector.** Resumes the frame's stored indicator state, feeds it the new bars and
   classifies each of them (``market_data.domain.trend``).
3. **Storage.** The readings (trend, indicators, confirmation checks, bar timestamps) and the
   new resume point are written in one transaction, so a bar is never processed twice.

A frame is therefore updated exactly when its bar closes: 1w once a week, 1d once a day, 4h six
times a day and 1h every hour, whatever the pass interval is.
"""

import logging
from collections.abc import Callable, Mapping
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from core.clock import Clock
from modules.exchanges.application.registry import ExchangeRegistry
from modules.exchanges.errors import RateLimited, TransientExchangeError, UnknownSymbolError
from modules.market_data.application.candle_fetch import fetch_candles_since
from modules.market_data.domain.models import Candle, Timeframe, find_gaps, floor_to_timeframe
from modules.market_data.domain.trend import (
    DEFAULT_SETTINGS,
    Bar,
    FrameTrend,
    TrendFrame,
    TrendSettings,
    build_bars,
    dump_indicators,
    frame_floor,
    load_indicators,
)
from modules.trends.application.ports import TrendStore
from modules.trends.domain.models import (
    FrameProgress,
    TrendRecord,
    WatchedSymbol,
    record_from_reading,
    settings_key,
)

logger = logging.getLogger(__name__)

TrendStoreFactory = Callable[[], AbstractAsyncContextManager[TrendStore]]

# Weekly first: its daily candles are then already stored when the daily frame is processed.
FRAME_ORDER = (TrendFrame.W1, TrendFrame.D1, TrendFrame.H4, TrendFrame.H1)
SOURCE_TIMEFRAME: Mapping[TrendFrame, Timeframe] = {
    TrendFrame.H1: Timeframe.H1,
    TrendFrame.H4: Timeframe.H4,
    TrendFrame.D1: Timeframe.D1,
    TrendFrame.W1: Timeframe.D1,  # the exchange has no weekly candle here: built from daily ones
}
_NO_PROGRESS_RETRY = timedelta(seconds=30)
_GAP_RETRY = timedelta(minutes=5)
_FAILURE_PAUSE = timedelta(minutes=1)
_UNKNOWN_SYMBOL_PAUSE = timedelta(hours=1)
_DEFAULT_RATE_LIMIT_PAUSE = timedelta(seconds=60)


@dataclass(frozen=True, slots=True)
class DetectorConfig:
    interval: timedelta = timedelta(seconds=60)  # how often a pass looks for closed bars
    grace: timedelta = timedelta(seconds=5)  # wait after a bar closes before asking for it
    warmup_bars: int = 150  # bars of history a frame starts from (it needs 55 to be complete)
    settings: Mapping[TrendFrame, TrendSettings] = field(
        default_factory=lambda: dict(DEFAULT_SETTINGS)
    )

    def __post_init__(self) -> None:
        for frame, cfg in self.settings.items():
            if self.warmup_bars < cfg.bars_needed + 2:
                raise ValueError(
                    f"warmup_bars must be at least {cfg.bars_needed + 2} for {frame.value}"
                )


def _to_bar(candle: Candle) -> Bar:
    return Bar(candle.open_time, candle.open, candle.high, candle.low, candle.close)


class TrendDetector:
    def __init__(
        self,
        stores: TrendStoreFactory,
        exchanges: ExchangeRegistry,
        clock: Clock,
        config: DetectorConfig | None = None,
    ) -> None:
        self._stores = stores
        self._exchanges = exchanges
        self._clock = clock
        self._config = config or DetectorConfig()
        self._last_run: datetime | None = None
        self._retry_at: dict[tuple[str, str, TrendFrame], datetime] = {}
        self._symbol_retry_at: dict[tuple[str, str], datetime] = {}
        self._rate_limited_until: dict[str, datetime] = {}
        self._reported_gaps: set[tuple[str, str, TrendFrame]] = set()

    async def run_if_due(self) -> int:
        """Readings written by this pass; 0 when it is not time yet or no bar had closed."""
        now = self._clock.now()
        if self._last_run is not None and now - self._last_run < self._config.interval:
            return 0
        self._last_run = now
        async with self._stores() as store:
            symbols = await store.trends.list_symbols(active_only=True)
        written = 0
        for symbol in symbols:
            written += await self._process_symbol(symbol, now)
        return written

    # --- one symbol --------------------------------------------------------------------------

    async def _process_symbol(self, symbol: WatchedSymbol, now: datetime) -> int:
        key = (symbol.exchange, symbol.symbol)
        paused_until = self._rate_limited_until.get(symbol.exchange)
        if paused_until is not None and now < paused_until:
            return 0
        if now < self._symbol_retry_at.get(key, now):
            return 0
        async with self._stores() as store:
            progress = await store.trends.get_progress(symbol.exchange, symbol.symbol)
        written = 0
        for frame in FRAME_ORDER:
            if frame not in self._config.settings:
                continue
            if now < self._retry_at.get((*key, frame), now):
                continue
            if not self._is_due(frame, progress.get(frame), now):
                continue
            try:
                written += await self._run_frame(symbol, frame, progress.get(frame), now)
            except RateLimited as exc:
                pause = (
                    timedelta(seconds=exc.retry_after_seconds)
                    if exc.retry_after_seconds is not None
                    else _DEFAULT_RATE_LIMIT_PAUSE
                )
                self._rate_limited_until[symbol.exchange] = now + pause
                logger.warning(
                    "%s rate limited the trend detector; paused for %.0fs",
                    symbol.exchange,
                    pause.total_seconds(),
                )
                break
            except UnknownSymbolError:
                self._symbol_retry_at[key] = now + _UNKNOWN_SYMBOL_PAUSE
                logger.warning(
                    "trend detector: %s is unknown on %s", symbol.symbol, symbol.exchange
                )
                break
            except TransientExchangeError as exc:
                self._symbol_retry_at[key] = now + _FAILURE_PAUSE
                logger.warning("trend detector: %s %s failed: %s", symbol.symbol, frame.value, exc)
                break
            except Exception:
                self._retry_at[(*key, frame)] = now + _FAILURE_PAUSE
                logger.exception("trend detector: %s %s failed", symbol.symbol, frame.value)
        return written

    def _is_due(self, frame: TrendFrame, progress: FrameProgress | None, now: datetime) -> bool:
        """A bar closed after the last one processed (or the frame was never processed)."""
        if progress is None:
            return True
        if progress.settings_key != settings_key(self._config.settings[frame]):
            return True
        newest_closed = frame_floor(frame, now - self._config.grace) - frame.delta
        return progress.last_bar_open_time < newest_closed

    # --- one timeframe -----------------------------------------------------------------------

    async def _run_frame(
        self,
        symbol: WatchedSymbol,
        frame: TrendFrame,
        progress: FrameProgress | None,
        now: datetime,
    ) -> int:
        cfg = self._config.settings[frame]
        if progress is not None and progress.settings_key != settings_key(cfg):
            async with self._stores() as store:  # other EMA lengths: start the frame over
                await store.trends.reset_frame(symbol.exchange, symbol.symbol, frame)
                await store.commit()
            progress = None
        closed_before = now - self._config.grace
        history_start = (
            frame_floor(frame, closed_before) - self._config.warmup_bars * frame.delta
            if progress is None
            else None
        )
        await self._sync_candles(symbol, SOURCE_TIMEFRAME[frame], history_start, now)
        return await self._classify(symbol, frame, cfg, progress, history_start, now)

    async def _sync_candles(
        self,
        symbol: WatchedSymbol,
        timeframe: Timeframe,
        history_start: datetime | None,
        now: datetime,
    ) -> None:
        """Store the closed candles that are missing; no request when none has closed."""
        delta = timeframe.delta
        closed_before = now - self._config.grace
        async with self._stores() as store:
            _, first, last = await store.candles.bounds(symbol.exchange, symbol.symbol, timeframe)
        source = self._exchanges.market_data(symbol.exchange)
        fetched: list[Candle] = []
        if last is None:
            start = history_start or (
                floor_to_timeframe(closed_before, timeframe) - self._config.warmup_bars * delta
            )
            fetched = await fetch_candles_since(source, symbol.symbol, timeframe, start, now)
        else:
            if history_start is not None and (first is None or first > history_start + delta):
                head = await fetch_candles_since(
                    source, symbol.symbol, timeframe, history_start, first or now
                )
                fetched += [c for c in head if first is None or c.open_time < first]
            if last + 2 * delta <= closed_before:  # the next candle has closed
                fetched += await fetch_candles_since(
                    source, symbol.symbol, timeframe, last + delta, now
                )
        closed = [c for c in fetched if c.open_time + delta <= closed_before]
        if not closed:
            return
        async with self._stores() as store:
            await store.candles.upsert_many(symbol.exchange, closed)
            await store.commit()

    async def _classify(
        self,
        symbol: WatchedSymbol,
        frame: TrendFrame,
        cfg: TrendSettings,
        progress: FrameProgress | None,
        history_start: datetime | None,
        now: datetime,
    ) -> int:
        timeframe = SOURCE_TIMEFRAME[frame]
        delta = timeframe.delta
        closed_before = now - self._config.grace
        key = (symbol.exchange, symbol.symbol, frame)
        start = history_start if progress is None else progress.last_bar_open_time + frame.delta
        assert start is not None
        async with self._stores() as store:
            stored = await store.candles.get_range(
                symbol.exchange, symbol.symbol, timeframe, start, closed_before
            )
        candles = [c for c in stored if c.open_time + delta <= closed_before]
        if not candles:
            self._retry_at[key] = now + _NO_PROGRESS_RETRY
            return 0
        gaps = find_gaps([c.open_time for c in candles], timeframe)
        if progress is None and gaps:
            # An old hole in the stored history: start from the stretch after the last one.
            cut = gaps[-1].end + delta
            candles = [c for c in candles if c.open_time >= cut]
            gaps = []
        elif gaps or (progress is not None and candles[0].open_time != start):
            if key not in self._reported_gaps:
                self._reported_gaps.add(key)
                logger.warning(
                    "trend detector: %s %s has missing %s candles; waiting for them",
                    symbol.symbol,
                    frame.value,
                    timeframe.value,
                )
            self._retry_at[key] = now + _GAP_RETRY
            return 0
        self._reported_gaps.discard(key)
        bars = (
            build_bars(candles, frame) if frame is TrendFrame.W1 else [_to_bar(c) for c in candles]
        )
        if progress is not None:
            bars = [b for b in bars if b.open_time > progress.last_bar_open_time]
        if not bars:
            self._retry_at[key] = now + _NO_PROGRESS_RETRY
            return 0

        engine = FrameTrend(frame, cfg)
        state = engine.initial_state() if progress is None else load_indicators(progress.state)
        records: list[TrendRecord] = []
        for bar in bars:
            state = engine.update(state, bar)
            record = record_from_reading(symbol.exchange, symbol.symbol, engine.read(state), now)
            if record is not None:
                records.append(record)
        async with self._stores() as store:
            await store.trends.upsert_records(records)
            await store.trends.save_progress(
                symbol.exchange,
                symbol.symbol,
                FrameProgress(frame, bars[-1].open_time, settings_key(cfg), dump_indicators(state)),
                now,
            )
            await store.commit()
        return len(records)
