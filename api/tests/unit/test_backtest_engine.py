from decimal import Decimal

import pytest

from factories import MARKET, T0, make_candles, make_config
from modules.analytics.domain.metrics import compute_metrics
from modules.backtesting.domain.engine import run_backtest
from modules.backtesting.domain.models import (
    BacktestConfig,
    InvalidBacktestConfig,
    hash_candles,
)
from modules.market_data.domain.models import Timeframe
from modules.strategies.domain.types import Side
from reference_ema_crossover import (
    EmaCrossoverParams,
    EmaCrossoverStrategy,
)

# Cross up is detected on the close of candle 3 (index); cross down on the close of candle 7.
CLOSES = [10, 10, 10, 12, 14, 16, 18, 14, 8, 4, 4]
# Opens deliberately differ from the previous close, to expose any look-ahead/fill-price mistake.
OPENS = [10, 10, 10, 11, 13, 15, 17, 16, 9, 5, 4]


def _strategy() -> EmaCrossoverStrategy:
    return EmaCrossoverStrategy(EmaCrossoverParams(2, 3))


def test_signals_fill_at_the_next_candle_open_never_the_signal_candle() -> None:
    candles = make_candles(CLOSES, OPENS)
    outcome = run_backtest(make_config(), candles, MARKET, _strategy())

    buy, sell = outcome.fills
    assert (buy.side, buy.time, buy.price) == (Side.BUY, candles[4].open_time, Decimal(13))
    assert (sell.side, sell.time, sell.price) == (Side.SELL, candles[8].open_time, Decimal(9))
    assert outcome.final_quantity == 0


def test_fees_and_slippage_are_applied_and_cash_is_conserved() -> None:
    candles = make_candles(CLOSES, OPENS)
    config = make_config(fee_rate="0.001", slippage_bps="10")
    outcome = run_backtest(config, candles, MARKET, _strategy())

    buy, sell = outcome.fills
    assert buy.price == Decimal(13) * Decimal("1.001")  # adverse slippage on buys
    assert sell.price == Decimal(9) * Decimal("0.999")  # and on sells
    assert buy.fee == buy.notional * Decimal("0.001")
    # Quantity is rounded down to the lot size and never costs more than the cash available.
    assert buy.quantity % MARKET.step_size == 0
    assert buy.notional + buy.fee <= config.initial_capital
    expected_cash = config.initial_capital - buy.notional - buy.fee + sell.notional - sell.fee
    assert outcome.final_cash == expected_cash
    assert outcome.equity_curve[-1].equity == expected_cash  # flat at the end


def test_equity_is_marked_at_each_candle_close() -> None:
    candles = make_candles(CLOSES, OPENS)
    outcome = run_backtest(make_config(), candles, MARKET, _strategy())
    buy = outcome.fills[0]
    # While holding, equity = cash + quantity * close.
    cash_after_buy = Decimal(1000) - buy.notional
    assert outcome.equity_curve[4].equity == cash_after_buy + buy.quantity * candles[4].close
    assert len(outcome.equity_curve) == len(candles)


def test_signal_on_last_candle_is_not_filled() -> None:
    candles = make_candles([10, 10, 10, 12])  # cross up on the very last candle
    outcome = run_backtest(make_config(), candles, MARKET, _strategy())
    assert outcome.fills == []
    assert outcome.unfilled_signals == 1


def test_order_below_exchange_minimum_is_rejected_not_filled() -> None:
    candles = make_candles(CLOSES, OPENS)
    outcome = run_backtest(make_config(capital="5"), candles, MARKET, _strategy())  # < min notional
    assert outcome.fills == []
    assert [r.side for r in outcome.rejected] == [Side.BUY]
    assert "minimum" in outcome.rejected[0].reason
    assert outcome.final_cash == Decimal(5)


def test_backtest_is_reproducible() -> None:
    candles = make_candles(CLOSES, OPENS)
    config = make_config(fee_rate="0.001", slippage_bps="5")
    first = run_backtest(config, candles, MARKET, _strategy())
    second = run_backtest(config, candles, MARKET, _strategy())
    assert first == second
    assert hash_candles(candles) == hash_candles(make_candles(CLOSES, OPENS))
    assert hash_candles(candles) != hash_candles(make_candles([*CLOSES[:-1], 5], OPENS))


def test_metrics_are_net_of_fees_and_include_benchmark() -> None:
    candles = make_candles(CLOSES, OPENS)
    config = make_config(fee_rate="0.001")
    outcome = run_backtest(config, candles, MARKET, _strategy())
    metrics = compute_metrics(
        initial_capital=config.initial_capital,
        equity_curve=outcome.equity_curve,
        fills=outcome.fills,
        first_price=outcome.first_price,
        last_price=outcome.last_price,
        open_position=outcome.final_quantity > 0,
        rejected_signals=len(outcome.rejected),
    )
    assert metrics.round_trips == 1
    assert metrics.fills == 2
    assert metrics.win_rate_pct == Decimal("0.0000")  # bought at 13, sold at 9: a loss
    assert metrics.net_pnl < 0
    assert metrics.fees_paid == sum((f.fee for f in outcome.fills), Decimal(0)).quantize(
        Decimal("0.00000001")
    )
    assert metrics.max_drawdown_pct > 0
    assert metrics.buy_and_hold_return_pct == Decimal("-60.0000")  # 10 -> 4
    assert metrics.open_position is False


def test_empty_data_and_bad_config_are_rejected() -> None:
    with pytest.raises(InvalidBacktestConfig):
        run_backtest(make_config(), [], MARKET, _strategy())
    base = {
        "exchange": "binance",
        "symbol": "BTC/USDT",
        "timeframe": Timeframe.H1,
        "start": T0,
        "end": T0 + Timeframe.H1.delta,
        "initial_capital": Decimal(1000),
        "fee_rate": Decimal("0.001"),
        "slippage_bps": Decimal(5),
        "strategy_type": "ema_crossover",
    }
    for override in (
        {"end": T0},
        {"initial_capital": Decimal(0)},
        {"fee_rate": Decimal(1)},
        {"slippage_bps": Decimal(-1)},
    ):
        with pytest.raises(InvalidBacktestConfig):
            BacktestConfig(**{**base, **override})  # type: ignore[arg-type]
