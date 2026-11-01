"""Book 2 ch. 7, O2: the optional slippage model of the backtest."""

from dataclasses import replace
from decimal import Decimal

import pytest

from factories import MARKET, T0, make_candles, make_config
from modules.backtesting.domain.engine import run_backtest
from modules.backtesting.domain.models import InvalidBacktestConfig
from modules.execution.domain.fills import SlippageModel, effective_slippage_bps
from modules.market_data.domain.models import Candle, Timeframe
from modules.strategies.domain.types import Side
from reference_ema_crossover import EmaCrossoverParams, EmaCrossoverStrategy

D = Decimal


def _candle(open_: str, high: str, low: str, close: str, volume: str) -> Candle:
    return Candle("BTC/USDT", Timeframe.H1, T0, D(open_), D(high), D(low), D(close), D(volume))


def _bps(model: SlippageModel, k_range: str, k_size: str, candle: Candle, notional: str) -> Decimal:
    return effective_slippage_bps(model, D(5), D(k_range), D(k_size), candle, D(notional))


def test_fixed_returns_the_base_whatever_the_coefficients_and_the_candle():
    wild = _candle("100", "200", "50", "100", "1")
    assert _bps(SlippageModel.FIXED, "9", "9", wild, "10000") == D(5)


def test_the_model_adds_the_range_term_and_the_size_term_by_hand():
    candle = _candle("100", "110", "90", "100", "10")  # range 20% = 2000 bps; traded 1000
    # size: 500 / 1000 = 50% = 5000 bps; 5 + 0.01*2000 + 0.01*5000 = 75
    assert _bps(SlippageModel.VOLATILITY_SIZE, "0.01", "0.01", candle, "500") == D(75)


def test_zero_coefficients_leave_the_base_and_it_never_goes_below_it():
    candle = _candle("100", "110", "90", "100", "10")
    assert _bps(SlippageModel.VOLATILITY_SIZE, "0", "0", candle, "500") == D(5)
    for notional in ("0", "1", "100", "100000"):
        assert _bps(SlippageModel.VOLATILITY_SIZE, "0.2", "0.3", candle, notional) >= D(5)


def test_a_candle_with_no_volume_has_no_size_term_and_the_total_is_capped():
    empty = _candle("100", "100", "100", "100", "0")
    assert _bps(SlippageModel.VOLATILITY_SIZE, "0", "5", empty, "1000") == D(5)
    huge = _candle("100", "300", "1", "100", "0.001")
    assert _bps(SlippageModel.VOLATILITY_SIZE, "50", "50", huge, "1000000") == D(9999)


def test_the_size_term_grows_with_the_order_and_the_range_term_with_the_range():
    calm = _candle("100", "101", "99", "100", "1000")
    wild = _candle("100", "110", "90", "100", "1000")
    small = _bps(SlippageModel.VOLATILITY_SIZE, "0.01", "0.01", calm, "100")
    large = _bps(SlippageModel.VOLATILITY_SIZE, "0.01", "0.01", calm, "50000")
    assert large > small
    assert _bps(SlippageModel.VOLATILITY_SIZE, "0.01", "0", wild, "0") > _bps(
        SlippageModel.VOLATILITY_SIZE, "0.01", "0", calm, "0"
    )


def test_negative_coefficients_are_refused():
    with pytest.raises(InvalidBacktestConfig):
        replace(make_config(), slippage_k_range=D(-1))
    with pytest.raises(InvalidBacktestConfig):
        replace(make_config(), slippage_k_size=D(-1))


CLOSES = [10, 10, 10, 12, 14, 16, 18, 14, 8, 4, 4, 4, 9, 12, 15, 18, 12, 6]


def _run(**overrides: object):
    config = replace(make_config(slippage_bps="5"), slippage_bps=D(5), **overrides)
    strategy = EmaCrossoverStrategy(EmaCrossoverParams(2, 3))
    candles = [replace(c, volume=D(1_000_000)) for c in make_candles(CLOSES)]
    return run_backtest(config, candles, MARKET, strategy)


def test_the_default_and_an_explicit_fixed_model_give_identical_results_bit_for_bit():
    default = _run()
    explicit = _run(slippage_model=SlippageModel.FIXED, slippage_k_range=D(3), slippage_k_size=D(3))
    assert default.fills and default.fills == explicit.fills
    assert default.equity_curve == explicit.equity_curve


def test_the_model_only_makes_every_fill_worse_than_the_fixed_one():
    fixed = _run()
    model = _run(
        slippage_model=SlippageModel.VOLATILITY_SIZE,
        slippage_k_range=D("0.5"),
        slippage_k_size=D("0.5"),
    )
    assert len(fixed.fills) == len(model.fills) > 1
    for before, after in zip(fixed.fills, model.fills, strict=True):
        assert before.side is after.side
        if after.side is Side.BUY:
            assert after.price >= before.price
        else:
            assert after.price <= before.price
    assert model.equity_curve[-1].equity <= fixed.equity_curve[-1].equity
    assert model.fills != fixed.fills  # and it did change something here


def test_an_all_in_order_against_a_thin_candle_saturates_the_cap_instead_of_overspending():
    thin = [replace(c, volume=D(1)) for c in make_candles(CLOSES)]
    config = replace(
        make_config(),
        slippage_model=SlippageModel.VOLATILITY_SIZE,
        slippage_k_size=D(1),
    )
    outcome = run_backtest(config, thin, MARKET, EmaCrossoverStrategy(EmaCrossoverParams(2, 3)))
    assert outcome.final_cash >= 0
    buy = next(f for f in outcome.fills if f.side is Side.BUY)
    assert buy.price <= thin[4].open * 2  # capped at 9,999 bps, never beyond


def test_cash_never_goes_negative_with_a_heavy_model():
    outcome = _run(
        slippage_model=SlippageModel.VOLATILITY_SIZE,
        slippage_k_range=D(5),
        slippage_k_size=D(5),
    )
    assert outcome.final_cash >= 0
    assert all(point.equity > 0 for point in outcome.equity_curve)
