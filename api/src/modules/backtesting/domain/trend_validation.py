"""Does the trend detector really identify trends? A forward-return study, with a null control.

A trend label is useful only if what comes *after* it differs from what comes after the opposite
label. For every completed bar of a timeframe the study takes the reading the detector had at
that bar's close (nothing from the future), enters at the *next* bar's open and measures the
return ``horizon`` bars later. Then, per state:

* mean / median forward return and the share of bars that moved the way the label says;
* the **edge**: mean return after BULLISH minus mean return after BEARISH. Market drift cancels
  out of that difference, so a bull market cannot fake it;
* a 95% interval of the edge from a block bootstrap (blocks as long as the horizon, because
  neighbouring forward windows overlap);
* the same numbers for confirmed trends and for each confirmation on its own, to see which of
  the four checks adds something;
* the edge in the first and the second half of the sample (a real effect shows in both);
* a **null control**: the same pipeline on random walks with the same volatility and no memory.
  An EMA stack shows up in pure noise too (about a third of the time), so the real edge only
  means something if it clearly beats what noise produces.
"""

import itertools
import math
import random
import statistics
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from modules.market_data.domain.models import Candle
from modules.market_data.domain.trend import (
    DEFAULT_SETTINGS,
    Bar,
    FrameTrend,
    Trend,
    TrendFrame,
    TrendReading,
    TrendSettings,
    build_bars,
)

DEFAULT_HORIZONS: Mapping[TrendFrame, int] = {
    TrendFrame.H1: 24,  # one day
    TrendFrame.H4: 12,  # two days
    TrendFrame.D1: 10,  # two weeks
    TrendFrame.W1: 8,  # two months
}
CHECKS = ("distance", "slope", "adx", "structure")
MIN_SAMPLES = 30  # below this a group's numbers are not worth reading


@dataclass(frozen=True, slots=True)
class Sample:
    """One bar whose forward return is known."""

    position: int
    reading: TrendReading
    forward_pct: float


@dataclass(frozen=True, slots=True)
class GroupStats:
    name: str
    count: int
    mean_pct: float | None
    median_pct: float | None
    #: Share of samples that moved the way the label says (up for bullish, down for bearish,
    #: up for the rest).
    hit_rate: float | None
    mean_abs_pct: float | None


@dataclass(frozen=True, slots=True)
class Edge:
    """Mean forward return after BULLISH minus after BEARISH, in percentage points."""

    value: float | None
    low: float | None  # 95% block-bootstrap interval
    high: float | None
    bullish_count: int
    bearish_count: int


@dataclass(frozen=True, slots=True)
class NullControl:
    simulations: int
    edge_mean: float
    edge_p95: float
    #: Share of simulated edges at or above the real one (a p-value).
    p_value: float | None


@dataclass(frozen=True, slots=True)
class FrameValidation:
    frame: TrendFrame
    horizon: int
    bars: int
    samples: int
    state_share: Mapping[Trend, float]
    mean_run_bars: Mapping[Trend, float]
    groups: tuple[GroupStats, ...]
    edge: Edge
    edge_confirmed: Edge
    edge_first_half: Edge
    edge_second_half: Edge
    null: NullControl | None

    @property
    def verdict(self) -> str:
        """A plain reading of the numbers (it never says more than they support)."""
        e = self.edge
        if e.value is None or e.low is None or e.high is None:
            return "not enough data"
        if min(e.bullish_count, e.bearish_count) < MIN_SAMPLES:
            return "not enough data"
        if e.low > 0 and (self.null is None or e.value > self.null.edge_p95):
            return "works: the edge is positive and beats noise"
        if e.high < 0:
            return "inverted: bearish labels were followed by higher prices"
        return "no demonstrated edge"


def forward_samples(
    bars: Sequence[Bar], frame: TrendFrame, settings: TrendSettings, horizon: int
) -> list[Sample]:
    """The reading at each bar's close paired with the return of the next ``horizon`` bars."""
    engine = FrameTrend(frame, settings)
    state = engine.initial_state()
    samples: list[Sample] = []
    for i, bar in enumerate(bars):
        state = engine.update(state, bar)
        reading = engine.read(state)
        if reading.trend is None or i + horizon >= len(bars):
            continue
        entry, exit_ = bars[i + 1].open, bars[i + horizon].close
        if entry <= 0:
            continue
        samples.append(Sample(i, reading, float((exit_ - entry) / entry * 100)))
    return samples


def _stats(name: str, samples: Sequence[Sample], bearish: bool = False) -> GroupStats:
    if not samples:
        return GroupStats(name, 0, None, None, None, None)
    returns = [s.forward_pct for s in samples]
    hits = sum(1 for r in returns if (r < 0 if bearish else r > 0))
    return GroupStats(
        name,
        len(returns),
        statistics.fmean(returns),
        statistics.median(returns),
        hits / len(returns),
        statistics.fmean(abs(r) for r in returns),
    )


def _is(
    trend: Trend, *, confirmed: bool = False, check: str | None = None
) -> Callable[[Sample], bool]:
    def test(sample: Sample) -> bool:
        r = sample.reading
        if r.trend is not trend:
            return False
        if confirmed and not r.confirmed:
            return False
        return check is None or r.checks.get(check) is True

    return test


def _edge(
    samples: Sequence[Sample],
    horizon: int,
    *,
    confirmed: bool = False,
    resamples: int = 1000,
    seed: int = 7,
) -> Edge:
    bull, bear = _is(Trend.BULLISH, confirmed=confirmed), _is(Trend.BEARISH, confirmed=confirmed)
    bull_returns = [s.forward_pct for s in samples if bull(s)]
    bear_returns = [s.forward_pct for s in samples if bear(s)]
    if not bull_returns or not bear_returns:
        return Edge(None, None, None, len(bull_returns), len(bear_returns))
    value = statistics.fmean(bull_returns) - statistics.fmean(bear_returns)
    if resamples <= 0:
        return Edge(value, None, None, len(bull_returns), len(bear_returns))

    # Non-overlapping blocks as long as the horizon; resample whole blocks with replacement.
    blocks: dict[int, list[float]] = {}  # block -> [bull_sum, bull_n, bear_sum, bear_n]
    for s in samples:
        cell = blocks.setdefault(s.position // max(horizon, 1), [0.0, 0.0, 0.0, 0.0])
        if bull(s):
            cell[0] += s.forward_pct
            cell[1] += 1
        elif bear(s):
            cell[2] += s.forward_pct
            cell[3] += 1
    cells = list(blocks.values())
    rng = random.Random(seed)
    draws: list[float] = []
    for _ in range(resamples):
        total = [0.0, 0.0, 0.0, 0.0]
        for _ in cells:
            cell = cells[rng.randrange(len(cells))]
            for k in range(4):
                total[k] += cell[k]
        if total[1] > 0 and total[3] > 0:
            draws.append(total[0] / total[1] - total[2] / total[3])
    if len(draws) < resamples // 2:
        return Edge(value, None, None, len(bull_returns), len(bear_returns))
    draws.sort()
    low, high = draws[int(0.025 * len(draws))], draws[int(0.975 * len(draws)) - 1]
    return Edge(value, low, high, len(bull_returns), len(bear_returns))


def _runs(readings: Sequence[TrendReading]) -> dict[Trend, float]:
    lengths: dict[Trend, list[int]] = {t: [] for t in Trend}
    current: Trend | None = None
    length = 0
    for r in readings:
        if r.trend is current:
            length += 1
            continue
        if current is not None:
            lengths[current].append(length)
        current, length = r.trend, 1
    if current is not None:
        lengths[current].append(length)
    return {t: (statistics.fmean(v) if v else 0.0) for t, v in lengths.items()}


def _random_walk(bars: Sequence[Bar], rng: random.Random) -> list[Bar]:
    """Bars with the volatility and wick size of ``bars`` but no memory and no drift."""
    closes = [float(b.close) for b in bars]
    returns = [math.log(b / a) for a, b in itertools.pairwise(closes) if a > 0 and b > 0]
    sigma = statistics.pstdev(returns)
    wick = statistics.fmean(float((b.high - b.low) / b.close) for b in bars if b.close > 0) / 2
    price, out = closes[0], []
    start = bars[0].open_time
    step = bars[1].open_time - bars[0].open_time if len(bars) > 1 else timedelta(hours=1)
    for i in range(len(bars)):
        opened = price
        price = opened * math.exp(rng.gauss(0.0, sigma))
        high = max(opened, price) * (1 + wick * rng.random())
        low = min(opened, price) * (1 - wick * rng.random())
        out.append(
            Bar(
                start + i * step,
                Decimal(repr(opened)),
                Decimal(repr(high)),
                Decimal(repr(low)),
                Decimal(repr(price)),
            )
        )
    return out


def null_control(
    bars: Sequence[Bar],
    frame: TrendFrame,
    settings: TrendSettings,
    horizon: int,
    real_edge: float | None,
    *,
    simulations: int = 20,
    seed: int = 11,
) -> NullControl:
    """Edge of the same detector on random walks like this market (no memory, no drift)."""
    rng = random.Random(seed)
    edges: list[float] = []
    for _ in range(simulations):
        walk = _random_walk(bars, rng)
        found = _edge(forward_samples(walk, frame, settings, horizon), horizon, resamples=0).value
        if found is not None:
            edges.append(found)
    if not edges:
        return NullControl(0, 0.0, 0.0, None)
    ordered = sorted(edges)
    p95 = ordered[min(len(ordered) - 1, int(0.95 * len(ordered)))]
    p_value = None if real_edge is None else sum(1 for e in edges if e >= real_edge) / len(edges)
    return NullControl(len(edges), statistics.fmean(edges), p95, p_value)


def validate_frame(
    bars: Sequence[Bar],
    frame: TrendFrame,
    settings: TrendSettings | None = None,
    horizon: int | None = None,
    *,
    null_simulations: int = 20,
) -> FrameValidation:
    """The full study of one timeframe over a series of completed bars."""
    cfg = DEFAULT_SETTINGS[frame] if settings is None else settings
    h = DEFAULT_HORIZONS[frame] if horizon is None else horizon
    if h < 1:
        raise ValueError("horizon must be >= 1")
    samples = forward_samples(bars, frame, cfg, h)
    engine = FrameTrend(frame, cfg)
    state, readings = engine.initial_state(), []
    for bar in bars:
        state = engine.update(state, bar)
        reading = engine.read(state)
        if reading.trend is not None:
            readings.append(reading)

    groups = [_stats("all", samples)]
    for trend in (Trend.BULLISH, Trend.BEARISH, Trend.SIDEWAYS):
        bearish = trend is Trend.BEARISH
        groups.append(_stats(trend.value, [s for s in samples if _is(trend)(s)], bearish))
        if trend is Trend.SIDEWAYS:
            continue
        groups.append(
            _stats(
                f"{trend.value} confirmed",
                [s for s in samples if _is(trend, confirmed=True)(s)],
                bearish,
            )
        )
        for check in CHECKS:
            groups.append(
                _stats(
                    f"{trend.value} + {check}",
                    [s for s in samples if _is(trend, check=check)(s)],
                    bearish,
                )
            )

    edge = _edge(samples, h)
    half = len(samples) // 2
    return FrameValidation(
        frame=frame,
        horizon=h,
        bars=len(bars),
        samples=len(samples),
        state_share={
            t: (sum(1 for r in readings if r.trend is t) / len(readings) if readings else 0.0)
            for t in Trend
        },
        mean_run_bars=_runs(readings),
        groups=tuple(groups),
        edge=edge,
        edge_confirmed=_edge(samples, h, confirmed=True),
        edge_first_half=_edge(samples[:half], h, resamples=300),
        edge_second_half=_edge(samples[half:], h, resamples=300),
        null=(
            null_control(bars, frame, cfg, h, edge.value, simulations=null_simulations)
            if null_simulations > 0 and len(bars) > 2
            else None
        ),
    )


def validate_candles(
    candles: Sequence[Candle],
    frames: Sequence[TrendFrame] = (TrendFrame.H1, TrendFrame.H4, TrendFrame.D1, TrendFrame.W1),
    settings: Mapping[TrendFrame, TrendSettings] | None = None,
    horizons: Mapping[TrendFrame, int] | None = None,
    *,
    null_simulations: int = 20,
) -> list[FrameValidation]:
    """Study every requested timeframe of one symbol, building the bars from its candles."""
    results = []
    for frame in frames:
        cfg = (DEFAULT_SETTINGS if settings is None else settings)[frame]
        horizon = (DEFAULT_HORIZONS if horizons is None else horizons)[frame]
        results.append(
            validate_frame(
                build_bars(candles, frame), frame, cfg, horizon, null_simulations=null_simulations
            )
        )
    return results


def _fmt(value: float | None, digits: int = 2, suffix: str = "") -> str:
    return "n/a" if value is None else f"{value:+.{digits}f}{suffix}"


def _edge_text(edge: Edge) -> str:
    if edge.value is None:
        return "n/a"
    interval = (
        "" if edge.low is None or edge.high is None else f" [{edge.low:+.2f}, {edge.high:+.2f}]"
    )
    return f"{edge.value:+.2f}{interval} (n {edge.bullish_count}/{edge.bearish_count})"


def format_report(
    symbol: str, results: Sequence[FrameValidation], since: datetime | None = None
) -> str:
    """A plain-text report of ``validate_candles`` for one symbol."""
    lines = [
        f"Trend validation — {symbol}" + ("" if since is None else f" (from {since:%Y-%m-%d})")
    ]
    for r in results:
        share = ", ".join(f"{t.value} {100 * v:.0f}%" for t, v in r.state_share.items())
        runs = ", ".join(f"{t.value} {v:.1f}" for t, v in r.mean_run_bars.items())
        lines += [
            "",
            f"[{r.frame.value}] horizon {r.horizon} bars | {r.bars} bars, {r.samples} readings",
            f"  time in state: {share}   mean run (bars): {runs}",
            f"  {'group':<22}{'n':>6}{'mean %':>9}{'median %':>10}{'hit':>7}{'|ret| %':>9}",
        ]
        for g in r.groups:
            hit = "n/a" if g.hit_rate is None else f"{100 * g.hit_rate:.0f}%"
            lines.append(
                f"  {g.name:<22}{g.count:>6}{_fmt(g.mean_pct):>9}{_fmt(g.median_pct):>10}"
                f"{hit:>7}{_fmt(g.mean_abs_pct, 2).lstrip('+'):>9}"
            )
        lines += [
            f"  edge bullish - bearish: {_edge_text(r.edge)} pp",
            f"  edge, confirmed only : {_edge_text(r.edge_confirmed)} pp",
            f"  edge by half         : first {_edge_text(r.edge_first_half)} | "
            f"second {_edge_text(r.edge_second_half)}",
        ]
        if r.null is not None:
            p = "n/a" if r.null.p_value is None else f"{r.null.p_value:.2f}"
            lines.append(
                f"  null (random walks, {r.null.simulations}): mean {r.null.edge_mean:+.2f}, "
                f"95th pct {r.null.edge_p95:+.2f}; p-value of the real edge {p}"
            )
        lines.append(f"  verdict: {r.verdict}")
    return "\n".join(lines)
