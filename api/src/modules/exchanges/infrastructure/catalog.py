"""Which exchange integrations exist, and which of them are active.

* ``AVAILABLE_EXCHANGES``: every integration implemented in the codebase (add a line when you
  write a new ``exchanges/infrastructure/<name>.py``).
* ``ENABLED_EXCHANGES`` (environment): the subset this deployment actually uses.
"""

from collections.abc import Sequence

from modules.exchanges.application.exchange import Exchange
from modules.exchanges.application.registry import ExchangeRegistry
from modules.exchanges.errors import ExchangeConfigurationError
from modules.exchanges.infrastructure.binance import BinanceExchange
from modules.exchanges.infrastructure.binance_usdm import BinanceUsdmExchange

AVAILABLE_EXCHANGES: dict[str, type[Exchange]] = {
    "binance": BinanceExchange,
    "binance-usdm": BinanceUsdmExchange,
}


def build_exchange_registry(enabled: Sequence[str] = ("binance",)) -> ExchangeRegistry:
    registry = ExchangeRegistry()
    for exchange_id in enabled:
        try:
            registry.register(AVAILABLE_EXCHANGES[exchange_id])
        except KeyError:
            raise ExchangeConfigurationError(
                f"ENABLED_EXCHANGES lists {exchange_id!r}, which has no integration "
                f"(available: {', '.join(sorted(AVAILABLE_EXCHANGES))})"
            ) from None
    if not registry.exchange_ids():
        raise ExchangeConfigurationError("ENABLED_EXCHANGES must enable at least one exchange")
    return registry
