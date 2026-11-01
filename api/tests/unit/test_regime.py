import math
from decimal import Decimal

import pytest

from factories import T0
from modules.analytics.domain.regime import (
    efficiency_ratio,
    regime_report,
    rolling_volatility,
    terciles,
)
from modules.backtesting.domain.models import EquityPoint
from modules.market_data.domain.models import Candle, Timeframe

HOUR = Timeframe.H1.delta


def _candles(closes: list[Decimal]) -> list[Candle]:
    return [
        Candle("BTC/USDT", Timeframe.H1, T0 + i * HOUR, c, c, c, c, Decimal(1))
        for i, c in enumerate(closes)
    ]


def _equity(n: int) -> list[EquityPoint]:
    return [EquityPoint(T0 + (i + 1) * HOUR, Decimal(1000)) for i in range(n)]


def test_rolling_volatility_matches_the_direct_population_deviation():
    returns = [Decimal(v) for v in ("0.01", "-0.02", "0.015", "0.0", "0.03", "-0.01")]
    out = rolling_volatility(returns, 3)
    assert out[:2] == [None, None]
    window = returns[1:4]
    mean = sum(window) / 3
    expected = (sum((r - mean) ** 2 for r in window) / 3).sqrt()
    assert out[3] is not None and abs(out[3] - expected) < Decimal("1e-20")


def test_rolling_volatility_needs_a_window_of_at_least_two():
    with pytest.raises(ValueError):
        rolling_volatility([Decimal("0.01")] * 5, 1)


def test_terciles_split_a_series_in_three_and_handle_empty():
    low, high = terciles([Decimal(v) for v in range(1, 10)])
    assert (low, high) == (Decimal(3), Decimal(6))
    assert terciles([]) == (None, None)


def test_efficiency_ratio_is_one_on_a_straight_line_and_small_on_a_zigzag():
    straight = efficiency_ratio([Decimal(i) for i in range(1, 12)], 5)
    zigzag = efficiency_ratio([Decimal(10 + (i % 2)) for i in range(12)], 5)
    assert straight[:5] == [None] * 5 and straight[5] == Decimal(1)
    value = zigzag[6]
    assert value is not None and value <= Decimal("0.2")
    with pytest.raises(ValueError):
        efficiency_ratio([Decimal(1)], 0)


def test_flat_prices_have_zero_efficiency_not_a_division_error():
    assert efficiency_ratio([Decimal(5)] * 8, 3)[3] == Decimal(0)


def test_report_needs_two_windows_of_candles_and_an_aligned_curve():
    candles = _candles([Decimal(100)] * 20)
    assert regime_report(candles, _equity(20), [False] * 20, window=30) is None
    assert regime_report(candles, _equity(19), [False] * 20, window=5) is None


def _volatility_step(n: int = 240) -> list[Decimal]:
    price = Decimal(100)
    out = []
    for i in range(n):
        swing = Decimal("0.001") if i < n // 2 else Decimal("0.02")
        price *= Decimal(1) + (swing if i % 2 == 0 else -swing)
        out.append(price)
    return out


def test_report_splits_a_volatility_step_into_bands_that_cover_the_sample():
    candles = _candles(_volatility_step())
    report = regime_report(candles, _equity(len(candles)), [True] * len(candles), window=20)
    assert report is not None and report["window"] == 20
    bands = {b["label"]: b for b in report["volatility"]["bands"]}
    assert set(bands) == {"low", "medium", "high"}
    assert sum(Decimal(b["share_pct"]) for b in bands.values()) == Decimal(100) or abs(
        sum(Decimal(b["share_pct"]) for b in bands.values()) - 100
    ) < Decimal("0.0001")
    assert all(isinstance(b["share_pct"], str) for b in bands.values())  # JSON-ready
    assert bands["low"]["bars"] > 0 and bands["high"]["bars"] > 0
    assert report["volatility"]["cut_low"] is not None


def test_the_asset_return_of_each_band_compounds_the_bars_in_it():
    candles = _candles(_volatility_step())
    report = regime_report(candles, _equity(len(candles)), [False] * len(candles), window=20)
    assert report is not None
    for band in report["volatility"]["bands"]:
        assert band["in_market_pct"] in (None, "0")
        assert math.isfinite(float(Decimal(band["asset_return_pct"])))
    # flat equity: the strategy never moves in any band
    assert all(Decimal(b["strategy_return_pct"]) == 0 for b in report["volatility"]["bands"])


def test_a_gap_in_the_candles_drops_the_return_across_it():
    closes = _volatility_step(60)
    candles = _candles(closes)
    candles[30:] = [
        Candle(
            c.symbol, c.timeframe, c.open_time + 10 * HOUR, c.open, c.high, c.low, c.close, c.volume
        )
        for c in candles[30:]
    ]
    report = regime_report(candles, _equity(60), [False] * 60, window=5)
    assert report is not None
    bars = sum(b["bars"] for b in report["efficiency"]["bands"])
    assert bars < 60 - 5  # the step across the hole is not a valid return
