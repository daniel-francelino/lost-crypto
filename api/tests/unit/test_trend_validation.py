"""The trend validation study, on markets whose answer is known."""

import math
import random
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from modules.backtesting.domain.trend_validation import (
    DEFAULT_HORIZONS,
    format_report,
    forward_samples,
    validate_candles,
    validate_frame,
)
from modules.market_data.domain.trend import (
    DEFAULT_SETTINGS,
    Bar,
    Trend,
    TrendFrame,
)

T0 = datetime(2020, 1, 1, tzinfo=UTC)
FRAME = TrendFrame.D1


def _bars_from_log_prices(path: list[float], rng: random.Random) -> list[Bar]:
    bars = []
    for i in range(1, len(path)):
        opened, closed = math.exp(path[i - 1]), math.exp(path[i])
        high = max(opened, closed) * (1 + 0.004 * rng.random())
        low = min(opened, closed) * (1 - 0.004 * rng.random())
        bars.append(
            Bar(
                T0 + timedelta(days=i),
                Decimal(repr(opened)),
                Decimal(repr(high)),
                Decimal(repr(low)),
                Decimal(repr(closed)),
            )
        )
    return bars


def _regime_market(n: int, seed: int, persistence: float = 0.985) -> list[Bar]:
    """Up and down regimes that last ~70 bars each: trends really exist here."""
    rng = random.Random(seed)
    path, direction = [math.log(100)], 1
    for _ in range(n):
        if rng.random() > persistence:
            direction = -direction
        path.append(path[-1] + direction * 0.006 + rng.gauss(0, 0.01))
    return _bars_from_log_prices(path, rng)


def _random_walk(n: int, seed: int, drift: float = 0.0) -> list[Bar]:
    rng = random.Random(seed)
    path = [math.log(100)]
    for _ in range(n):
        path.append(path[-1] + drift + rng.gauss(0, 0.01))
    return _bars_from_log_prices(path, rng)


def _mean_reverting(n: int, seed: int) -> list[Bar]:
    rng = random.Random(seed)
    path = [math.log(100)]
    for _ in range(n):
        path.append(path[-1] - 0.15 * (path[-1] - math.log(100)) + rng.gauss(0, 0.01))
    return _bars_from_log_prices(path, rng)


def test_forward_return_enters_at_the_next_open_and_exits_at_the_horizon_close() -> None:
    bars = _random_walk(200, seed=1)
    cfg = DEFAULT_SETTINGS[FRAME]
    samples = forward_samples(bars, FRAME, cfg, horizon=5)
    sample = samples[0]
    i = sample.position
    expected = float((bars[i + 5].close - bars[i + 1].open) / bars[i + 1].open * 100)
    assert sample.forward_pct == pytest.approx(expected)
    assert i == cfg.slow - 1  # the first bar with a trend reading
    assert samples[-1].position == len(bars) - 1 - 5  # no sample without a known outcome


def test_the_reading_used_never_depends_on_later_bars() -> None:
    bars = _regime_market(400, seed=2)
    cfg = DEFAULT_SETTINGS[FRAME]
    full = forward_samples(bars, FRAME, cfg, horizon=10)
    cut = forward_samples(bars[:300], FRAME, cfg, horizon=10)
    for a, b in zip(cut, full, strict=False):
        assert a.reading == b.reading  # same decision with or without the future


def test_a_market_with_real_trends_shows_a_positive_edge_that_beats_noise() -> None:
    result = validate_frame(_regime_market(2000, seed=3), FRAME, null_simulations=5)
    assert result.edge.value is not None and result.edge.value > 1.0
    assert result.edge.low is not None and result.edge.low > 0
    assert result.edge_first_half.value is not None and result.edge_first_half.value > 0
    assert result.edge_second_half.value is not None and result.edge_second_half.value > 0
    assert result.null is not None and result.edge.value > result.null.edge_p95
    assert result.verdict.startswith("works")
    by_name = {g.name: g for g in result.groups}
    assert by_name["bullish"].mean_pct is not None and by_name["bearish"].mean_pct is not None
    assert by_name["bullish"].mean_pct > by_name["bearish"].mean_pct


def test_a_random_walk_is_not_called_a_working_detector() -> None:
    verdicts = [
        validate_frame(_random_walk(1800, seed=s), FRAME, null_simulations=0).verdict
        for s in (4, 5, 6)
    ]
    assert not any(v.startswith("works") for v in verdicts)


def test_market_drift_alone_does_not_create_an_edge() -> None:
    """A rising market makes every label look good in absolute terms; the edge cancels it."""
    result = validate_frame(_random_walk(1800, seed=7, drift=0.002), FRAME, null_simulations=0)
    by_name = {g.name: g for g in result.groups}
    assert by_name["all"].mean_pct is not None and by_name["all"].mean_pct > 1.0
    assert result.edge.value is not None and abs(result.edge.value) < 1.5
    assert not result.verdict.startswith("works") or (result.edge.low or 0) > 0


def test_a_mean_reverting_market_inverts_the_edge() -> None:
    result = validate_frame(_mean_reverting(1800, seed=8), FRAME, null_simulations=0)
    assert result.edge.value is not None and result.edge.value < 0
    assert result.verdict.startswith("inverted")


def test_too_little_data_is_reported_as_such() -> None:
    result = validate_frame(_regime_market(120, seed=9), FRAME, null_simulations=0)
    assert result.verdict == "not enough data"


def test_the_study_covers_confirmations_and_runs() -> None:
    result = validate_frame(_regime_market(1500, seed=10), FRAME, null_simulations=0)
    names = {g.name for g in result.groups}
    assert {"all", "bullish", "bearish", "sideways", "bullish confirmed"} <= names
    assert {"bullish + adx", "bearish + structure", "bullish + slope"} <= names
    assert result.mean_run_bars[Trend.BULLISH] > 1
    assert sum(result.state_share.values()) == pytest.approx(1.0)
    assert result.edge_confirmed.bullish_count <= result.edge.bullish_count


def test_candles_in_report_out() -> None:
    from factories import make_candles

    closes = [str(round(100 + 0.05 * i + 8 * math.sin(i / 40), 2)) for i in range(24 * 150)]
    results = validate_candles(
        make_candles(closes, start=T0),
        frames=(TrendFrame.H4, TrendFrame.D1),
        null_simulations=1,
    )
    assert [r.frame for r in results] == [TrendFrame.H4, TrendFrame.D1]
    assert results[0].horizon == DEFAULT_HORIZONS[TrendFrame.H4]
    report = format_report("BTCUSDT", results, since=T0)
    assert "Trend validation — BTCUSDT" in report and "[4h]" in report and "[1d]" in report
    assert "verdict:" in report and "edge bullish - bearish" in report
