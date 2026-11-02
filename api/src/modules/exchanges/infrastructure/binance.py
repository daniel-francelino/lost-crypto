"""Binance spot: the single file with everything specific to this exchange.

Implements the ``Exchange`` contract on top of the shared CCXT base. To add another exchange,
copy this file, change the profile and the hooks, and register the class in ``catalog.py``.
"""

from decimal import Decimal
from typing import Any

from modules.exchanges.domain.connections import ApiPermissions
from modules.exchanges.domain.models import (
    ExchangeCapabilities,
    ExchangeProfile,
    FeeSchedule,
    OrderType,
)
from modules.exchanges.infrastructure.ccxt_exchange import CcxtExchange
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
        has_demo=True,  # demo-api.binance.com, Demo Mode keys
        timeframes=frozenset(Timeframe),
    ),
    # Regular tier without BNB discount; refine per account when real fees are reconciled.
    fees=FeeSchedule(maker_rate=Decimal("0.001"), taker_rate=Decimal("0.001")),
)


class BinanceExchange(CcxtExchange):
    PROFILE = BINANCE_PROFILE
    CCXT_EXCHANGE_ID = "binance"

    async def fetch_api_permissions(self) -> ApiPermissions:
        """Binance's ``GET /sapi/v1/account/apiRestrictions`` (mainnet only; not on the testnet)."""
        self._require_authentication()
        raw = await self._call(lambda: self._client.sapiGetAccountApiRestrictions())
        return ApiPermissions(
            can_read=bool(raw.get("enableReading")),
            can_trade=bool(raw.get("enableSpotAndMarginTrading")),
            can_withdraw=bool(raw.get("enableWithdrawals")),
            can_transfer=bool(
                raw.get("enableInternalTransfer") or raw.get("permitsUniversalTransfer")
            ),
            ip_restricted=bool(raw.get("ipRestrict")),
        )

    def parse_market(self, symbol: str, market: dict[str, Any]) -> MarketInfo | None:
        """Exact rules from Binance's exchange filters (None when they are not present)."""
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
