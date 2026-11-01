"""Two simple reference strategies (EMA crossover and Donchian breakout) are not part of the
product; the tests keep them as stand-ins that are easy to reason about. They join the catalog
for the test session only."""

from modules.strategies import catalog
from reference_donchian_breakout import DonchianBreakoutStrategy
from reference_ema_crossover import EmaCrossoverStrategy

catalog.AVAILABLE_STRATEGIES = (
    EmaCrossoverStrategy,
    DonchianBreakoutStrategy,
    *catalog.AVAILABLE_STRATEGIES,
)
