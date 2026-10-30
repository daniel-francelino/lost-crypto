"""Everything that is specific to Binance spot, in one place."""

from decimal import Decimal
from typing import Any

from modules.exchanges.domain.models import (
    ExchangeCapabilities,
    ExchangeProfile,
    FeeSchedule,
    OrderType,
)
from modules.exchanges.infrastructure.ccxt_adapter import CcxtMarketDataSource
from modules.market_data.domain.models import MarketInfo, Timeframe

BINANCE_ID = "binance"

BINANCE_PROFILE = ExchangeProfile(
    capabilities=ExchangeCapabilities(
        exchange_id=BINANCE_ID,
        name="Binance (spot)",
        order_types=frozenset(
            {OrderType.MARKET, OrderType.LIMIT, OrderType.STOP_LOSS, OrderType.TAKE_PROFIT}
        ),
        native_stop_orders=True,  # STOP_LOSS_LIMIT / OCO live on the exchange
        max_client_order_id_length=36,  # newClientOrderId
        has_testnet=True,  # testnet.binance.vision, separate API keys
        timeframes=frozenset(Timeframe),
    ),
    # Regular tier without BNB discount; refine per account when real fees are reconciled.
    fees=FeeSchedule(maker_rate=Decimal("0.001"), taker_rate=Decimal("0.001")),
)


def binance_market_info(symbol: str, market: dict[str, Any]) -> MarketInfo | None:
    """Exact trading rules from Binance's exchange filters (None if they are not present)."""
    filters = {f["filterType"]: f for f in (market.get("info") or {}).get("filters", [])}
    lot = filters.get("LOT_SIZE")
    price = filters.get("PRICE_FILTER")
    notional = filters.get("NOTIONAL") or filters.get("MIN_NOTIONAL")
    if not (lot and price):
        return None
    return MarketInfo(
        symbol=symbol,
        step_size=Decimal(lot["stepSize"]),
        tick_size=Decimal(price["tickSize"]),
        min_quantity=Decimal(lot["minQty"]),
        min_notional=Decimal((notional or {}).get("minNotional", "0")),
    )


def create_binance_market_data() -> CcxtMarketDataSource:
    return CcxtMarketDataSource(BINANCE_ID, market_parser=binance_market_info)
