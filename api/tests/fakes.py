from modules.exchanges.application.registry import ExchangeRegistry
from modules.exchanges.infrastructure.binance import BINANCE_PROFILE
from modules.market_data.application.ports import MarketDataSource


def fake_registry(source: MarketDataSource) -> ExchangeRegistry:
    """An exchange registry whose 'binance' serves deterministic data instead of the network."""
    registry = ExchangeRegistry()
    registry.register(BINANCE_PROFILE, lambda: source)
    return registry
