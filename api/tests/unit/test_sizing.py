"""Advisory sizing (book 1 ch. 6) and the tail-risk inputs stored with a backtest."""

from datetime import timedelta
from decimal import Decimal

import pytest

from factories import T0
from modules.analytics.domain.sizing import (
    growth_rate,
    half_kelly,
    kelly_fraction,
    suggest_fraction,
    tail_cap,
    worst_period_loss,
)
from modules.analytics.domain.tail_risk import strategy_loss_to_return, tail_risk
from modules.backtesting.domain.models import EquityPoint
from modules.market_data.domain.models import Candle, Timeframe

D = Decimal
HOUR = timedelta(hours=1)


def _close(value: Decimal, expected: str, tolerance: str = "0.0005") -> bool:
    return abs(value - D(expected)) <= D(tolerance)


def test_book_example_6_2_kelly_and_growth():
    excess_mean, std, risk_free = D("0.0723"), D("0.1691"), D("0.04")  # 11.23% - 4%
    variance = std**2
    f = kelly_fraction(excess_mean, variance)
    assert f is not None and _close(f, "2.528", "0.001")
    assert _close(growth_rate(f, excess_mean, variance, risk_free), "0.1314")
    assert _close(growth_rate(D(1), excess_mean, variance, risk_free), "0.0980")


def test_book_example_6_1_leverage_one_with_no_edge_loses_half_a_variance():
    assert growth_rate(D(1), D(0), D("0.01") ** 2) == D("-0.00005")


def test_kelly_has_no_answer_without_variance():
    assert kelly_fraction(D("0.1"), D(0)) is None
    assert kelly_fraction(D("0.1"), D("-1")) is None


def test_half_kelly_halves_and_never_goes_negative():
    assert half_kelly(D(2)) == D(1)
    assert half_kelly(D("-0.5")) == D(0)


def test_worst_loss_is_none_on_short_samples_and_when_nothing_lost():
    assert worst_period_loss([D("-0.1")] * 29) is None
    assert worst_period_loss([D("0.01")] * 40) is None
    returns = [D("0.01")] * 39 + [D("-0.07")]
    assert worst_period_loss(returns) == D(7)


def test_tail_cap_is_the_tolerable_loss_over_the_worst_loss():
    assert tail_cap(D(10), D(5)) == D(2)
    assert tail_cap(D(10), None) is None
    assert tail_cap(D(10), D(0)) is None


def test_scaling_the_returns_divides_the_cap_by_the_same_factor():
    base = [D("0.01")] * 39 + [D("-0.04")]
    scaled = [r * 3 for r in base]
    cap_base = tail_cap(D(10), worst_period_loss(base))
    cap_scaled = tail_cap(D(10), worst_period_loss(scaled))
    assert cap_base is not None and cap_scaled is not None
    assert abs(cap_scaled - cap_base / 3) < D("1e-20")


def test_suggestion_is_never_above_one_nor_above_the_operators_fraction():
    big = suggest_fraction(D(1), D(5), [("tail_asset", D(8))])
    assert big.value == D(1) and big.binding == "spot_limit"
    small = suggest_fraction(D("0.4"), D(5), [])
    assert small.value <= D("0.4")


def test_the_binding_limit_is_the_smallest_one():
    result = suggest_fraction(D(1), D("0.8"), [("tail_strategy", D("0.3")), ("tail_asset", D(2))])
    assert (result.value, result.binding) == (D("0.3"), "tail_strategy")
    assert suggest_fraction(D(1), D("0.2"), [("tail_strategy", D(2))]).binding == "half_kelly"


def test_no_edge_gives_zero_and_a_negative_cap_is_floored():
    assert suggest_fraction(D(1), D("-1"), []).value == D(0)
    assert suggest_fraction(D(1), None, [("tail_asset", D("-2"))]).value == D(0)


def _candles(closes: list[Decimal]) -> list[Candle]:
    return [
        Candle("BTC/USDT", Timeframe.H1, T0 + i * HOUR, c, c, c, c, D(1))
        for i, c in enumerate(closes)
    ]


def _curve(values: list[Decimal], skip: set[int] | None = None) -> list[EquityPoint]:
    return [
        EquityPoint(T0 + (i + 1) * HOUR, v) for i, v in enumerate(values) if i not in (skip or ())
    ]


def test_tail_risk_finds_the_known_crash_and_its_time():
    values = [D(1000)] * 60
    values[40:] = [D(800)] * 20  # a 20% drop in one bar
    candles = _candles([D(100)] * 59 + [D(90)])
    block = tail_risk(_curve(values), candles, HOUR)
    assert D(block["strategy"]["worst_bar_loss_pct"]) == D(20)
    assert block["strategy"]["worst_bar_at"].startswith("2024-01-02T17:00")  # T0 + 41 h
    assert block["kelly_inputs"]["returns"] == 59 and block["returns"] == 59
    assert block["asset"]["worst_bar_return_pct"] is not None
    assert D(block["asset"]["worst_bar_return_pct"]) < 0


def test_tail_risk_counts_a_hole_instead_of_hiding_it():
    values = [D(1000) + i for i in range(60)]
    block = tail_risk(_curve(values, skip={20, 21, 22}), _candles([D(100)] * 60), HOUR)
    assert block["kelly_inputs"]["gaps"] >= 1


def test_tail_risk_is_null_below_the_minimum_sample():
    values = [D(1000)] * 10
    values[5] = D(900)
    block = tail_risk(_curve(values), _candles([D(100)] * 10), HOUR)
    assert block["strategy"]["worst_bar_loss_pct"] is None
    assert block["kelly_inputs"]["variance"] is not None  # the inputs are still stored


def test_strategy_loss_to_return_flips_the_sign():
    assert strategy_loss_to_return("20") == "-20"
    assert strategy_loss_to_return(None) is None


@pytest.mark.parametrize("flat", [True])
def test_a_flat_curve_has_no_loss_and_no_kelly_variance(flat: bool):
    block = tail_risk(_curve([D(1000)] * 60), _candles([D(100)] * 60), HOUR)
    assert block["strategy"]["worst_bar_loss_pct"] is None
    assert D(block["kelly_inputs"]["variance"]) == 0
