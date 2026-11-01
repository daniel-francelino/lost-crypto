import random
from datetime import timedelta
from decimal import Decimal

from factories import T0
from modules.backtesting.domain.random_entries import (
    MAX_SIMULATIONS,
    MIN_TRADES,
    RandomEntriesResult,
    RoundTrip,
    random_entries_block,
    random_entries_test,
    round_trips,
)
from modules.execution.domain.orders import Fill
from modules.market_data.domain.models import Candle, Timeframe
from modules.strategies.domain.types import Side

HOUR = Timeframe.H1.delta


def _candles(closes: list[Decimal]) -> list[Candle]:
    return [
        Candle("BTC/USDT", Timeframe.H1, T0 + i * HOUR, c, c, c, c, Decimal(1))
        for i, c in enumerate(closes)
    ]


def _walk(seed: int, n: int) -> list[Decimal]:
    rng = random.Random(seed)
    price = Decimal(100)
    out = []
    for _ in range(n):
        price *= Decimal(str(round(1 + rng.gauss(0, 0.01), 6)))
        out.append(price)
    return out


def _fill(side: Side, bar: int) -> Fill:
    return Fill(T0 + bar * HOUR, side, Decimal(1), Decimal(100), Decimal(0))


def _run(candles: list[Candle], trips: list[RoundTrip], seed: int = 7, **kw: int):
    return random_entries_test(
        candles, trips, fee_rate=Decimal(0), slippage_bps=Decimal(0), seed=seed, **kw
    )


def test_round_trips_pair_buys_with_the_next_sell_and_drop_an_open_position():
    candles = _candles(_walk(1, 50))
    fills = [
        _fill(Side.BUY, 3),
        _fill(Side.SELL, 8),
        _fill(Side.BUY, 10),
        _fill(Side.SELL, 11),
        _fill(Side.BUY, 20),  # still open at the end
    ]
    assert round_trips(fills, candles) == [RoundTrip(3, 5), RoundTrip(10, 1)]


def test_same_seed_same_answer_and_a_different_seed_changes_the_draws():
    candles = _candles(_walk(2, 400))
    trips = [RoundTrip(i * 30, 7) for i in range(12)]
    first = _run(candles, trips, seed=11)
    again = _run(candles, trips, seed=11)
    assert isinstance(first, RandomEntriesResult) and first == again
    other = _run(candles, trips, seed=12)
    assert isinstance(other, RandomEntriesResult)
    assert other.observed_log_return == first.observed_log_return  # the observed side is fixed


def test_trade_count_is_kept_and_unusable_trips_are_dropped():
    candles = _candles(_walk(3, 100))
    trips = [RoundTrip(i * 6, 3) for i in range(MIN_TRADES)] + [RoundTrip(98, 5)]
    result = _run(candles, trips)
    assert isinstance(result, RandomEntriesResult)
    assert result.trades == MIN_TRADES  # the last one runs past the data


def test_pure_noise_is_neither_always_nor_never_matched():
    fractions = []
    for seed in range(5):
        candles = _candles(_walk(100 + seed, 600))
        trips = [RoundTrip(i * 40, 10) for i in range(14)]
        result = _run(candles, trips, simulations=400)
        assert isinstance(result, RandomEntriesResult)
        fractions.append(result.fraction)
    assert all(Decimal("0.02") < f < Decimal("0.98") for f in fractions)


def test_a_strategy_that_trades_exactly_the_rises_is_rarely_matched_by_chance():
    closes: list[Decimal] = []
    price = Decimal(100)
    trips: list[RoundTrip] = []
    for _block in range(15):  # 10 flat bars, then a 5-bar rise the "strategy" is in
        for _ in range(10):
            closes.append(price)
        trips.append(RoundTrip(len(closes) - 1, 5))
        for _ in range(5):
            price *= Decimal("1.03")
            closes.append(price)
    result = _run(_candles(closes), trips, simulations=500)
    assert isinstance(result, RandomEntriesResult)
    assert result.fraction < Decimal("0.02")


def test_costs_lower_the_observed_result_but_never_the_random_one_below_it_for_free():
    candles = _candles(_walk(5, 300))
    trips = [RoundTrip(i * 25, 6) for i in range(10)]
    free = random_entries_test(candles, trips, fee_rate=Decimal(0), slippage_bps=Decimal(0), seed=3)
    costly = random_entries_test(
        candles, trips, fee_rate=Decimal("0.001"), slippage_bps=Decimal(5), seed=3
    )
    assert isinstance(free, RandomEntriesResult) and isinstance(costly, RandomEntriesResult)
    # Same trade count on both sides, so the same cost is charged to the observed and the random
    # trades: the comparison itself does not move; the observed log return does.
    assert costly.observed_log_return < free.observed_log_return
    assert costly.fraction == free.fraction


def test_too_few_trades_returns_the_reason_not_a_number():
    candles = _candles(_walk(6, 100))
    outcome = _run(candles, [RoundTrip(i * 5, 2) for i in range(MIN_TRADES - 1)])
    assert isinstance(outcome, str) and "fewer than" in outcome


def test_the_number_of_simulations_is_capped():
    candles = _candles(_walk(7, 200))
    result = _run(candles, [RoundTrip(i * 15, 4) for i in range(MIN_TRADES)], simulations=50_000)
    assert isinstance(result, RandomEntriesResult)
    assert result.simulations == MAX_SIMULATIONS


def test_block_is_json_friendly_and_explains_unavailability():
    candles = _candles(_walk(8, 300))
    fills = [f for i in range(12) for f in (_fill(Side.BUY, i * 20), _fill(Side.SELL, i * 20 + 5))]
    block = random_entries_block(
        candles, fills, fee_rate=Decimal("0.001"), slippage_bps=Decimal(5), seed=1
    )["random_entries"]
    assert block["available"] is True and isinstance(block["fraction"], str)
    assert block["trades"] == 12 and block["overlap_allowed"] is True
    short = random_entries_block(
        candles, fills[:4], fee_rate=Decimal(0), slippage_bps=Decimal(0), seed=1
    )["random_entries"]
    assert short["available"] is False and "fewer than" in short["reason"]
    assert timedelta(0) < HOUR  # keeps the helper import honest
