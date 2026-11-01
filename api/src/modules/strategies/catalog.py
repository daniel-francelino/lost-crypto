"""Which strategies exist, and which of them are active.

* ``AVAILABLE_STRATEGIES``: every strategy implemented in the codebase (add one line when you
  write a new file in ``strategies/domain/``).
* ``ENABLED_STRATEGIES`` (environment, comma separated): restrict a deployment to a subset, e.g.
  to keep an experimental strategy off a production worker. Empty (default) enables all.
"""

from collections.abc import Sequence
from typing import Any

from modules.strategies.domain.base import Strategy
from modules.strategies.domain.donchian_breakout import DonchianBreakoutStrategy
from modules.strategies.domain.ema_crossover import EmaCrossoverStrategy
from modules.strategies.domain.mean_reversion_zscore import MeanReversionZScoreStrategy
from modules.strategies.domain.registry import StrategyConfigurationError, StrategyRegistry

AVAILABLE_STRATEGIES: tuple[type[Strategy[Any]], ...] = (
    EmaCrossoverStrategy,
    DonchianBreakoutStrategy,
    MeanReversionZScoreStrategy,
)


def build_strategy_registry(enabled: Sequence[str] = ()) -> StrategyRegistry:
    by_key = {s.TYPE_KEY: s for s in AVAILABLE_STRATEGIES}
    selected = list(AVAILABLE_STRATEGIES)
    if enabled:
        unknown = [key for key in enabled if key not in by_key]
        if unknown:
            raise StrategyConfigurationError(
                f"ENABLED_STRATEGIES lists {unknown}, which have no implementation "
                f"(available: {', '.join(sorted(by_key))})"
            )
        selected = [by_key[key] for key in enabled]
    return StrategyRegistry(selected)
