import random
from decimal import Decimal

import pytest

from modules.analytics.domain import risk_ratios
from modules.analytics.domain.significance import (
    CRITICAL_VALUES,
    sharpe_t_stat,
    significance_level,
)


def _returns(seed: int, n: int, drift: str) -> list[Decimal]:
    rng = random.Random(seed)
    return [Decimal(str(round(rng.gauss(0, 0.01), 6))) + Decimal(drift) for _ in range(n)]


@pytest.mark.parametrize(("p_value", "critical"), CRITICAL_VALUES)
def test_levels_switch_exactly_at_the_book_critical_values(p_value: Decimal, critical: Decimal):
    assert significance_level(critical) == p_value
    assert significance_level(critical + Decimal("0.001")) == p_value


def test_below_the_loosest_critical_value_there_is_no_level():
    assert significance_level(Decimal("1.281")) is None
    assert significance_level(Decimal("-3")) is None


def test_book_table_values():
    assert [str(c) for _, c in CRITICAL_VALUES] == ["3.091", "2.326", "1.645", "1.282"]


def test_t_stat_is_per_bar_sharpe_times_root_n():
    returns = _returns(1, 400, "0.001")
    per_bar = risk_ratios.sharpe(returns, Decimal(1))
    assert per_bar is not None
    t_stat = sharpe_t_stat(returns)
    assert t_stat is not None
    assert abs(t_stat - per_bar * Decimal(400).sqrt()) < Decimal("1e-20")


def test_t_stat_grows_with_the_root_of_the_sample_for_the_same_sharpe():
    base = _returns(2, 100, "0.002")
    t_short = sharpe_t_stat(base)
    t_long = sharpe_t_stat(base * 4)
    assert t_short is not None
    assert t_long is not None
    # Repeating the sample keeps the mean; the std is nearly equal, so t doubles (sqrt(4)).
    assert Decimal("1.9") < t_long / t_short < Decimal("2.1")


def test_short_sample_has_no_statistic():
    assert sharpe_t_stat(_returns(3, risk_ratios.MIN_RETURNS - 1, "0.01")) is None


def test_a_planted_edge_is_significant_and_pure_noise_mostly_is_not():
    edge = sharpe_t_stat(_returns(4, 2000, "0.001"))
    assert edge is not None
    assert significance_level(edge) is not None
    significant = 0
    for seed in range(20):
        t_stat = sharpe_t_stat(_returns(100 + seed, 500, "0"))
        assert t_stat is not None
        if significance_level(t_stat) in {Decimal("0.05"), Decimal("0.01"), Decimal("0.001")}:
            significant += 1
    assert significant <= 3  # ~5% expected at p<0.05; the seeds are fixed, so this is stable


def test_constant_returns_have_no_statistic():
    assert sharpe_t_stat([Decimal("0.001")] * 60) is None
