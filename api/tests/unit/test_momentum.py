"""Book 2 ch. 6, O1: the lagged-return correlation grid."""

import random
from decimal import Decimal

import pytest

from modules.analytics.domain.momentum import (
    MAX_CELLS,
    MIN_PAIRS,
    critical_z,
    lagged_return_grid,
    pair_count,
)


def _prices(seed: int, n: int, persistence: float) -> list[Decimal]:
    """Returns with an AR(1) structure: positive persistence is momentum, negative reverts."""
    rng = random.Random(seed)
    price, last = 100.0, 0.0
    out = []
    for _ in range(n):
        last = persistence * last + rng.gauss(0, 0.01)
        price *= 1 + last
        out.append(Decimal(str(round(price, 8))))
    return out


def test_pairs_do_not_overlap_and_the_count_is_exact():
    # every max(L, H) candles: 100 candles, L=5, H=5 -> t = 5, 10, ..., 90 (95 + 5 is past the end)
    assert pair_count(100, 5, 5) == 18
    assert pair_count(100, 10, 2) == 9  # t = 10, 20, ..., 90 (90 + 2 <= 99)
    assert pair_count(10, 8, 8) == 0
    assert pair_count(5, 10, 1) == 0


def test_persistent_returns_show_positive_significant_correlation_at_short_lags():
    cells, alpha, _ = lagged_return_grid(_prices(1, 6000, 0.35), [1, 2], [1, 2])
    by = {(c.lookback, c.holding): c for c in cells}
    first = by[(1, 1)]
    assert first.correlation is not None and first.correlation > Decimal("0.2")
    assert first.significant_corrected is True
    assert abs(alpha - Decimal("0.05") / 4) < Decimal("1e-20")


def test_reverting_returns_show_a_negative_correlation():
    cells, _, _ = lagged_return_grid(_prices(2, 6000, -0.35), [1], [1])
    assert cells[0].correlation is not None and cells[0].correlation < Decimal("-0.2")
    assert cells[0].significant_corrected is True


def test_a_random_walk_has_almost_no_significant_cell_after_the_correction():
    flagged = 0
    for seed in range(10):
        cells, _, _ = lagged_return_grid(
            _prices(100 + seed, 3000, 0.0), [1, 5, 10, 25], [1, 5, 10, 25]
        )
        flagged += sum(1 for c in cells if c.significant_corrected)
    assert flagged <= 3  # 160 cells at a corrected 0.05/16: a couple of false hits at most


def test_a_cell_with_too_few_samples_says_why_instead_of_a_number():
    cells, _, _ = lagged_return_grid(_prices(3, 100, 0.0), [50], [50])
    assert cells[0].correlation is None and cells[0].z_stat is None
    assert cells[0].reason == "too few independent samples" and cells[0].n < MIN_PAIRS


def test_a_series_without_spread_has_no_correlation():
    cells, _, _ = lagged_return_grid([Decimal(100)] * 500, [1], [1])
    assert cells[0].correlation is None and cells[0].reason == "no spread in the returns"


def test_the_corrected_level_divides_by_the_number_of_cells():
    _, alpha_one, critical_one = lagged_return_grid(_prices(4, 500, 0.0), [1], [1])
    _, alpha_many, critical_many = lagged_return_grid(_prices(4, 500, 0.0), [1, 2, 3], [1, 2, 3])
    assert alpha_one == Decimal("0.05")
    assert abs(alpha_many - Decimal("0.05") / 9) < Decimal("1e-20")
    assert critical_many > critical_one


def test_the_critical_value_matches_the_normal_table():
    assert abs(critical_z(Decimal("0.05")) - Decimal("1.959964")) < Decimal("0.00001")
    assert abs(critical_z(Decimal("0.01")) - Decimal("2.575829")) < Decimal("0.00001")


def test_invalid_grids_are_refused():
    with pytest.raises(ValueError):
        lagged_return_grid(_prices(5, 100, 0.0), [0], [1])
    with pytest.raises(ValueError):
        lagged_return_grid(_prices(5, 100, 0.0), list(range(1, 12)), list(range(1, 12)))
    assert MAX_CELLS == 100


def test_results_are_deterministic():
    prices = _prices(6, 800, 0.2)
    assert lagged_return_grid(prices, [1, 5], [1, 5]) == lagged_return_grid(prices, [1, 5], [1, 5])
