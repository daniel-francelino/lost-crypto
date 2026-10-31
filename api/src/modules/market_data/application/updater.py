"""Keeps stored candles current: extends every followed series up to the last closed candle."""

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from core.clock import Clock
from modules.exchanges.application.registry import ExchangeRegistry
from modules.exchanges.errors import RateLimited, TransientExchangeError, UnknownSymbolError
from modules.market_data.application.service import BATCH_SIZE, ImportStoreFactory
from modules.market_data.domain.models import Timeframe, find_gaps, floor_to_timeframe

logger = logging.getLogger(__name__)

_DEFAULT_RATE_LIMIT_PAUSE = timedelta(seconds=60)
_MAX_FAILURE_PAUSE = timedelta(minutes=5)
_UNKNOWN_SYMBOL_PAUSE = timedelta(hours=1)


@dataclass(frozen=True, slots=True)
class Series:
    exchange: str
    symbol: str
    timeframe: Timeframe


@dataclass(frozen=True, slots=True)
class StaleSeries:
    series: Series
    last_open_time: datetime
    missing_candles: int


@dataclass(frozen=True, slots=True)
class RateLimitPause:
    exchange: str
    until: datetime


@dataclass(frozen=True, slots=True)
class UpdateReport:
    stale: tuple[StaleSeries, ...] = ()
    rate_limited: tuple[RateLimitPause, ...] = ()


@dataclass(frozen=True, slots=True)
class UpdaterConfig:
    interval: timedelta  # how often the worker looks for series with a newly closed candle
    grace: timedelta  # wait after a candle closes before asking the exchange for it
    discover_every: timedelta  # how often the followed series (and recent gaps) are refreshed
    max_age: timedelta  # stored series whose last candle is older than this are left alone
    stale_after_candles: int  # closed candles missing before a series is reported as stale
    repair_window_candles: int = 500


FollowedSeries = Callable[[], Awaitable[set[Series]]]


class CandleUpdater:
    """Worker-side. Only closed candles are written (idempotent upserts), only series that
    already hold candles are extended, and at most one request per series per pass is made.

    A series is followed when it is used by a bot that is not stopped, or when its last stored
    candle is recent (``max_age``): an old, abandoned import is never revived by itself. Gaps in
    the recent window are refetched. After a 429/418 nothing is sent to that exchange until the
    ``Retry-After`` the exchange gave has passed.
    """

    def __init__(
        self,
        stores: ImportStoreFactory,
        exchanges: ExchangeRegistry,
        clock: Clock,
        followed: FollowedSeries,
        config: UpdaterConfig,
    ) -> None:
        self._stores = stores
        self._exchanges = exchanges
        self._clock = clock
        self._followed = followed
        self._config = config
        self._last: dict[Series, datetime] = {}
        self._repair_from: dict[Series, datetime] = {}
        self._retry_at: dict[Series, datetime] = {}
        self._failures: dict[Series, int] = {}
        self._rate_limited_until: dict[str, datetime] = {}
        self._last_run: datetime | None = None
        self._last_discovery: datetime | None = None

    async def run_if_due(self) -> int:
        """Candles written by this pass; 0 when it is not time yet or nothing was due."""
        now = self._clock.now()
        if self._last_run is not None and now - self._last_run < self._config.interval:
            return 0
        self._last_run = now
        if (
            self._last_discovery is None
            or now - self._last_discovery >= self._config.discover_every
        ):
            await self._discover(now)
            self._last_discovery = now
        written = 0
        for series in sorted(self._last, key=lambda s: (s.exchange, s.timeframe.delta, s.symbol)):
            written += await self._update_series(series, now)
        return written

    def report(self) -> UpdateReport:
        now = self._clock.now()
        stale: list[StaleSeries] = []
        for series, last in self._last.items():
            delta = series.timeframe.delta
            expected = floor_to_timeframe(now - self._config.grace, series.timeframe) - delta
            missing = (expected - last) // delta
            if missing >= self._config.stale_after_candles:
                stale.append(StaleSeries(series, last, missing))
        paused = tuple(
            RateLimitPause(exchange, until)
            for exchange, until in sorted(self._rate_limited_until.items())
            if until > now
        )
        return UpdateReport(tuple(stale), paused)

    async def _discover(self, now: datetime) -> None:
        followed = await self._followed()
        async with self._stores() as store:
            stored = await store.candles.list_series(now - self._config.max_age)
            last: dict[Series, datetime] = {
                Series(exchange, symbol, timeframe): at
                for exchange, symbol, timeframe, at in stored
            }
            for series in followed - last.keys():
                at = await store.candles.last_open_time(
                    series.exchange, series.symbol, series.timeframe
                )
                if at is not None:  # a series without any candle is not backfilled here
                    last[series] = at
            repair: dict[Series, datetime] = {}
            for series, at in last.items():
                delta = series.timeframe.delta
                window_start = at - self._config.repair_window_candles * delta
                times = await store.candles.open_times(
                    series.exchange, series.symbol, series.timeframe, window_start, at + delta
                )
                gaps = find_gaps(times, series.timeframe)
                if gaps:
                    repair[series] = gaps[0].start
        self._last = last
        self._repair_from = repair
        self._retry_at = {s: t for s, t in self._retry_at.items() if s in last}
        self._failures = {s: n for s, n in self._failures.items() if s in last}

    async def _update_series(self, series: Series, now: datetime) -> int:
        paused_until = self._rate_limited_until.get(series.exchange)
        if paused_until is not None and now < paused_until:
            return 0
        if now < self._retry_at.get(series, now):
            return 0
        delta = series.timeframe.delta
        last = self._last[series]
        repair_from = self._repair_from.get(series)
        start = repair_from if repair_from is not None else last + delta
        closed_before = now - self._config.grace
        if repair_from is None and start + delta > closed_before:
            return 0  # the next candle has not closed yet: no request at all
        try:
            source = self._exchanges.market_data(series.exchange)
            fetched = await source.fetch_candles(series.symbol, series.timeframe, start, BATCH_SIZE)
        except RateLimited as exc:
            pause = (
                timedelta(seconds=exc.retry_after_seconds)
                if exc.retry_after_seconds is not None
                else _DEFAULT_RATE_LIMIT_PAUSE
            )
            self._rate_limited_until[series.exchange] = now + pause
            logger.warning(
                "%s rate limited candle updates; paused for %.0fs",
                series.exchange,
                pause.total_seconds(),
            )
            return 0
        except UnknownSymbolError:
            self._retry_at[series] = now + _UNKNOWN_SYMBOL_PAUSE
            logger.warning("candle update: %s is unknown on %s", series.symbol, series.exchange)
            return 0
        except TransientExchangeError as exc:
            self._back_off(series, now)
            logger.warning("candle update of %s failed: %s", series.symbol, exc)
            return 0
        except Exception:
            self._back_off(series, now)
            logger.exception("candle update of %s failed", series.symbol)
            return 0
        self._failures.pop(series, None)
        closed = [
            c for c in fetched if start <= c.open_time and c.open_time + delta <= closed_before
        ]
        self._repair_from.pop(series, None)
        if not closed:
            return 0
        async with self._stores() as store:
            written = await store.candles.upsert_many(series.exchange, closed)
            await store.commit()
        self._last[series] = max(last, max(c.open_time for c in closed))
        return written

    def _back_off(self, series: Series, now: datetime) -> None:
        failures = self._failures.get(series, 0) + 1
        self._failures[series] = failures
        pause = min(timedelta(seconds=60 * 2 ** (failures - 1)), _MAX_FAILURE_PAUSE)
        self._retry_at[series] = now + pause
