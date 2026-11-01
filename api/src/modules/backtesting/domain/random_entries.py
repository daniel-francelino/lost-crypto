"""Random-entries significance test (Chan, book 2 ch. 1, C6, pp. 20-22; after Lo et al.).

Keep the number of trades and how long each one lasts, but draw the entry bars at random on the
observed prices: how often does a strategy that enters at random do as well as this one? The
test and the gaussian one of ``analytics.domain.significance`` define "chance" differently and may
disagree. Nothing here says the strategy will work out of sample.

Every trade is scored the same way, the log return from the close of the entry bar to the close of
the exit bar minus the round-trip cost, so the observed trades and the random ones are comparable.
Entries may overlap (long-only trades drawn independently): a simplification, stated in the result.
"""

from bisect import bisect_right
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal, localcontext
from random import Random
from typing import Any

from modules.execution.domain.orders import Fill
from modules.market_data.domain.models import Candle
from modules.strategies.domain.types import Side

SIMULATIONS = 1_000
MAX_SIMULATIONS = 2_000  # a hard cap keeps the run time predictable
MIN_TRADES = 10  # below this, a fraction of simulations means nothing
_PRECISION = 40
_BPS = Decimal(10_000)


@dataclass(frozen=True, slots=True)
class RoundTrip:
    entry_index: int
    bars: int  # at least 1


@dataclass(frozen=True, slots=True)
class RandomEntriesResult:
    simulations: int
    as_good_or_better: int
    fraction: Decimal
    trades: int
    seed: int
    observed_log_return: Decimal


def round_trips(fills: Sequence[Fill], candles: Sequence[Candle]) -> list[RoundTrip]:
    """Pair each BUY with the next SELL (long-only); an open position at the end is dropped.
    A fill is placed on the bar that contains its time."""
    opens = [c.open_time for c in candles]

    def bar_of(fill: Fill) -> int:
        return max(0, bisect_right(opens, fill.time) - 1)

    trips: list[RoundTrip] = []
    entry: int | None = None
    for fill in sorted(fills, key=lambda f: f.time):
        if fill.side is Side.BUY and entry is None:
            entry = bar_of(fill)
        elif fill.side is Side.SELL and entry is not None:
            exit_ = bar_of(fill)
            trips.append(RoundTrip(entry, max(1, exit_ - entry)))
            entry = None
    return trips


def _round_trip_cost(fee_rate: Decimal, slippage_bps: Decimal) -> Decimal:
    return 2 * (fee_rate + slippage_bps / _BPS)


def random_entries_test(
    candles: Sequence[Candle],
    trips: Sequence[RoundTrip],
    *,
    fee_rate: Decimal,
    slippage_bps: Decimal,
    seed: int,
    simulations: int = SIMULATIONS,
) -> RandomEntriesResult | str:
    """The result, or the reason it cannot be computed (a string)."""
    n = len(candles)
    usable = [t for t in trips if t.entry_index + t.bars < n]
    if len(usable) < MIN_TRADES:
        return f"fewer than {MIN_TRADES} completed trades: the test needs more"
    runs = min(max(simulations, 1), MAX_SIMULATIONS)
    with localcontext() as ctx:
        ctx.prec = _PRECISION
        logs = [c.close.ln() for c in candles]
        cost = _round_trip_cost(fee_rate, slippage_bps)
        observed = sum(
            (logs[t.entry_index + t.bars] - logs[t.entry_index] - cost for t in usable), Decimal(0)
        )
        rng = Random(seed)
        better = 0
        for _ in range(runs):
            total = Decimal(0)
            for trip in usable:
                start = rng.randint(0, n - 1 - trip.bars)
                total += logs[start + trip.bars] - logs[start] - cost
            if total >= observed:
                better += 1
    return RandomEntriesResult(
        runs, better, Decimal(better) / Decimal(runs), len(usable), seed, observed
    )


def random_entries_block(
    candles: Sequence[Candle],
    fills: Sequence[Fill],
    *,
    fee_rate: Decimal,
    slippage_bps: Decimal,
    seed: int,
) -> dict[str, Any]:
    """The JSON stored with a run (numbers as strings); ``available`` is false with a reason."""
    outcome = random_entries_test(
        candles,
        round_trips(fills, candles),
        fee_rate=fee_rate,
        slippage_bps=slippage_bps,
        seed=seed,
    )
    if isinstance(outcome, str):
        return {"random_entries": {"available": False, "reason": outcome}}
    return {
        "random_entries": {
            "available": True,
            "simulations": outcome.simulations,
            "as_good_or_better": outcome.as_good_or_better,
            "fraction": str(outcome.fraction),
            "trades": outcome.trades,
            "seed": outcome.seed,
            "observed_log_return": str(outcome.observed_log_return),
            "overlap_allowed": True,
        }
    }
