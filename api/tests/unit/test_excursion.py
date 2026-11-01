"""Book 2 ch. 8, O3: maximum adverse excursion of each trade."""

from datetime import timedelta
from decimal import Decimal

from factories import T0
from modules.analytics.domain.excursion import WORST_LISTED, adverse_excursions
from modules.execution.domain.orders import Fill
from modules.market_data.domain.models import Candle, Timeframe
from modules.strategies.domain.types import Side

D = Decimal
HOUR = timedelta(hours=1)


def _candles(lows: list[str]) -> list[Candle]:
    return [
        Candle("BTC/USDT", Timeframe.H1, T0 + i * HOUR, D(100), D(110), D(low), D(100), D(1))
        for i, low in enumerate(lows)
    ]


def _fill(side: Side, bar: int, price: str = "100") -> Fill:
    return Fill(T0 + bar * HOUR, side, D(1), D(price), D(0))


def test_the_excursion_is_the_deepest_low_between_entry_and_exit_in_percent():
    candles = _candles(["99", "95", "80", "97", "50", "60"])
    fills = [_fill(Side.BUY, 1), _fill(Side.SELL, 3)]
    report = adverse_excursions(fills, candles)
    assert report is not None
    assert D(report["worst_pct"]) == D(20)  # the low of 80 in bar 2; the 50 is after the exit
    assert report["trades"] == 1


def test_a_trade_that_never_dips_below_its_entry_has_zero():
    candles = _candles(["100", "101", "105", "103"])
    report = adverse_excursions([_fill(Side.BUY, 0, "95"), _fill(Side.SELL, 2, "105")], candles)
    assert report is not None and D(report["worst_pct"]) == 0


def test_several_trades_give_worst_median_p95_and_the_worst_listed_first():
    lows = ["100"] * 60
    fills: list[Fill] = []
    depths = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    for i, depth in enumerate(depths):
        entry_bar = i * 6
        lows[entry_bar + 1] = str(100 - depth)
        fills += [_fill(Side.BUY, entry_bar), _fill(Side.SELL, entry_bar + 3)]
    report = adverse_excursions(fills, _candles(lows))
    assert report is not None and report["trades"] == 10
    assert D(report["worst_pct"]) == D(10)
    assert D(report["median_pct"]) == D(5)  # the lower middle of 1..10
    assert D(report["p95_pct"]) == D(10)
    listed = [D(t["pct"]) for t in report["worst_trades"]]
    assert listed == [D(10), D(9), D(8), D(7), D(6)] and len(listed) == WORST_LISTED


def test_an_open_position_at_the_end_is_ignored_and_no_trade_gives_none():
    candles = _candles(["100"] * 10)
    assert adverse_excursions([_fill(Side.BUY, 2)], candles) is None
    assert adverse_excursions([], candles) is None
    assert adverse_excursions([_fill(Side.BUY, 0), _fill(Side.SELL, 1)], []) is None


def test_a_sell_without_a_buy_is_ignored():
    candles = _candles(["100"] * 6)
    report = adverse_excursions(
        [_fill(Side.SELL, 0), _fill(Side.BUY, 1), _fill(Side.SELL, 3)], candles
    )
    assert report is not None and report["trades"] == 1


def test_timestamps_are_iso_and_numbers_are_strings():
    report = adverse_excursions(
        [_fill(Side.BUY, 1), _fill(Side.SELL, 4)], _candles(["99", "90", "92", "95", "99"])
    )
    assert report is not None
    trade = report["worst_trades"][0]
    assert trade["entry_at"].startswith("2024-01-01T01:00") and isinstance(trade["pct"], str)
    assert isinstance(report["worst_pct"], str)
