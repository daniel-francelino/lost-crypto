"""Two simple reference strategies (EMA crossover and Donchian breakout) are not part of the
product; the tests keep them as stand-ins that are easy to reason about. They join the catalog
for the test session only."""

import os

from modules.strategies import catalog
from reference_donchian_breakout import DonchianBreakoutStrategy
from reference_ema_crossover import EmaCrossoverStrategy

catalog.AVAILABLE_STRATEGIES = (
    EmaCrossoverStrategy,
    DonchianBreakoutStrategy,
    *catalog.AVAILABLE_STRATEGIES,
)


# The developer's api/.env (JWT secret, credential master keys, trading switches) configures the
# running stack, not the tests: without this, a JWT secret there turns authentication on and
# every test that sends no token gets a 401. Tests pass the settings they need explicitly.
for _name, _value in (
    ("JWT_SECRET", ""),
    ("CREDENTIAL_MASTER_KEYS", ""),
    ("API_TOKEN", ""),
    ("TESTNET_TRADING_ENABLED", "false"),
    ("FUTURES_PAPER_ENABLED", "false"),
    ("LIVE_TRADING_ENABLED", "false"),
    ("SYMBOL_REGISTRY_ENFORCED", "false"),
):
    os.environ[_name] = _value
