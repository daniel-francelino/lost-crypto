from modules.exchanges.application.registry import ExchangeRegistry
from modules.exchanges.infrastructure.binance import BINANCE_PROFILE, create_binance_market_data


def build_exchange_registry() -> ExchangeRegistry:
    """The exchanges this deployment supports. Add new exchanges here."""
    registry = ExchangeRegistry()
    registry.register(BINANCE_PROFILE, create_binance_market_data)
    return registry
