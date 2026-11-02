"""Binance USDⓈ-M perpetual integration, isolated from the Binance Spot adapter."""

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from modules.exchanges.application.ports import (
    ExchangePosition,
    MarketOrderRequest,
    StopOrderRequest,
    VenueOrder,
)
from modules.exchanges.domain.connections import ApiPermissions
from modules.exchanges.domain.models import (
    ExchangeCapabilities,
    ExchangeProfile,
    FeeSchedule,
    MarginMode,
    OrderType,
    PositionSide,
    TradingProduct,
)
from modules.exchanges.errors import ExchangeError, ExchangeRejected
from modules.exchanges.infrastructure.ccxt_exchange import CcxtExchange
from modules.market_data.domain.models import Candle, FundingRate, MarketInfo, MarkPrice, Timeframe

BINANCE_USDM_ID = "binance-usdm"
MAX_LEVERAGE = 10

BINANCE_USDM_PROFILE = ExchangeProfile(
    capabilities=ExchangeCapabilities(
        exchange_id=BINANCE_USDM_ID,
        name="Binance USD-M Perpetual",
        order_types=frozenset({OrderType.MARKET, OrderType.STOP_LOSS}),
        native_stop_orders=True,
        max_client_order_id_length=36,
        has_testnet=True,
        timeframes=frozenset(Timeframe),
        products=frozenset({TradingProduct.LINEAR_PERPETUAL}),
        max_leverage=MAX_LEVERAGE,
        has_demo=True,  # demo-fapi.binance.com, Futures Demo keys
    ),
    fees=FeeSchedule(maker_rate=Decimal("0.0002"), taker_rate=Decimal("0.0005")),
)


class BinanceUsdmExchange(CcxtExchange):
    PROFILE = BINANCE_USDM_PROFILE
    CCXT_EXCHANGE_ID = "binanceusdm"

    def is_supported_market(self, market: dict[str, Any]) -> bool:
        return bool(
            market.get("swap")
            and market.get("linear")
            and market.get("settle") == "USDT"
            and market.get("active")
        )

    def parse_market(self, symbol: str, market: dict[str, Any]) -> MarketInfo | None:
        filters = {
            item["filterType"]: item for item in (market.get("info") or {}).get("filters", [])
        }
        lot = filters.get("LOT_SIZE")
        price = filters.get("PRICE_FILTER")
        notional = filters.get("MIN_NOTIONAL") or filters.get("NOTIONAL")
        if lot is None or price is None:
            return None
        return MarketInfo(
            symbol=symbol,
            step_size=Decimal(lot["stepSize"]),
            tick_size=Decimal(price["tickSize"]),
            min_quantity=Decimal(lot["minQty"]),
            min_notional=Decimal(
                (notional or {}).get("notional", (notional or {}).get("minNotional", "0"))
            ),
        )

    async def fetch_mark_price(self, symbol: str) -> MarkPrice:
        raw = await self._call(lambda: self._client.fetch_mark_price(symbol))
        return MarkPrice(
            symbol=symbol,
            price=Decimal(str(raw["mark"])),
            timestamp=datetime.fromtimestamp(int(raw["timestamp"]) / 1000, UTC),
        )

    async def fetch_mark_candles(
        self, symbol: str, timeframe: Timeframe, since: datetime, limit: int
    ) -> list[Candle]:
        rows = await self._call(
            lambda: self._client.fetch_ohlcv(
                symbol, timeframe.value, int(since.timestamp() * 1000), limit, {"price": "mark"}
            )
        )
        return [
            Candle(
                symbol=symbol,
                timeframe=timeframe,
                open_time=datetime.fromtimestamp(int(row[0]) / 1000, UTC),
                open=Decimal(str(row[1])),
                high=Decimal(str(row[2])),
                low=Decimal(str(row[3])),
                close=Decimal(str(row[4])),
                volume=Decimal(str(row[5])),
            )
            for row in rows
        ]

    async def fetch_funding_rates(
        self, symbol: str, since: datetime, limit: int
    ) -> list[FundingRate]:
        rows = await self._call(
            lambda: self._client.fetch_funding_rate_history(
                symbol, int(since.timestamp() * 1000), limit
            )
        )
        return [
            FundingRate(
                symbol=symbol,
                rate=Decimal(str(row["fundingRate"])),
                funding_time=datetime.fromtimestamp(int(row["timestamp"]) / 1000, UTC),
                mark_price=(
                    Decimal(str(row["markPrice"])) if row.get("markPrice") is not None else None
                ),
            )
            for row in rows
            if row.get("fundingRate") is not None and row.get("timestamp") is not None
        ]

    async def fetch_api_permissions(self) -> ApiPermissions:
        self._require_authentication()
        raw = await self._call(lambda: self._client.sapiGetAccountApiRestrictions())
        return ApiPermissions(
            can_read=bool(raw.get("enableReading")),
            can_trade=bool(raw.get("enableFutures")),
            can_withdraw=bool(raw.get("enableWithdrawals")),
            can_transfer=bool(
                raw.get("enableInternalTransfer") or raw.get("permitsUniversalTransfer")
            ),
            ip_restricted=bool(raw.get("ipRestrict")),
            can_trade_derivatives=bool(raw.get("enableFutures")),
        )

    async def fetch_positions(self, symbols: list[str] | None = None) -> list[ExchangePosition]:
        """Read non-zero USD-M positions and normalize Binance/CCXT account fields."""
        self._require_authentication()
        raws = await self._call(lambda: self._client.fetch_positions(symbols))
        positions: list[ExchangePosition] = []
        for raw in raws:
            info = raw.get("info") or {}
            contracts = _optional_decimal(raw.get("contracts"))
            if contracts is None:
                contracts = abs(_optional_decimal(info.get("positionAmt")) or Decimal(0))
            else:
                contracts = abs(contracts)
            if contracts <= 0:
                continue
            raw_side = raw.get("side")
            if raw_side not in (PositionSide.LONG.value, PositionSide.SHORT.value):
                amount = _optional_decimal(info.get("positionAmt"))
                if amount is None or amount == 0:
                    raise ExchangeError("Binance USD-M returned an open position without a side")
                raw_side = PositionSide.LONG.value if amount > 0 else PositionSide.SHORT.value
            raw_margin_mode = raw.get("marginMode")
            try:
                margin_mode = MarginMode(raw_margin_mode) if raw_margin_mode is not None else None
            except ValueError:
                raise ExchangeError(
                    "Binance USD-M returned an unknown position margin mode"
                ) from None
            isolated_margin = (
                _optional_decimal(info.get("isolatedWallet"))
                if margin_mode is MarginMode.ISOLATED
                else None
            )
            if isolated_margin is None and margin_mode is MarginMode.ISOLATED:
                isolated_margin = _optional_decimal(raw.get("initialMargin"))
            positions.append(
                ExchangePosition(
                    symbol=str(raw.get("symbol") or ""),
                    side=PositionSide(raw_side),
                    quantity=contracts,
                    entry_price=_positive_decimal(raw.get("entryPrice")),
                    mark_price=_positive_decimal(raw.get("markPrice")),
                    unrealized_pnl=_optional_decimal(raw.get("unrealizedPnl")) or Decimal(0),
                    leverage=_optional_integer(raw.get("leverage")),
                    margin_mode=margin_mode,
                    isolated_margin=isolated_margin,
                    liquidation_price=_positive_decimal(raw.get("liquidationPrice")),
                    notional=_positive_decimal(raw.get("notional")),
                )
            )
        return positions

    async def prepare_market_order(self, request: MarketOrderRequest) -> None:
        if request.product is not TradingProduct.LINEAR_PERPETUAL:
            raise ExchangeRejected("Binance USD-M accepts only linear perpetual orders")
        if request.margin_mode is not MarginMode.ISOLATED:
            raise ExchangeRejected("Binance USD-M bots currently require isolated margin")
        if request.leverage > self.capabilities.max_leverage:
            raise ExchangeRejected("leverage exceeds the Binance USD-M adapter limit")

    async def prepare_market_configuration(
        self,
        product: TradingProduct,
        symbol: str,
        leverage: int,
        margin_mode: MarginMode | None,
        max_notional: Decimal | None = None,
    ) -> None:
        if product is not TradingProduct.LINEAR_PERPETUAL:
            raise ExchangeRejected("Binance USD-M accepts only linear perpetual markets")
        if margin_mode is not MarginMode.ISOLATED:
            raise ExchangeRejected("Binance USD-M requires isolated margin")
        if not 1 <= leverage <= self.capabilities.max_leverage:
            raise ExchangeRejected(
                f"leverage must be between 1x and {self.capabilities.max_leverage}x"
            )
        await self._call(self._client.load_markets)
        try:
            market = self._client.market(symbol)
        except Exception as exc:
            raise ExchangeRejected(f"unknown Binance USD-M perpetual symbol {symbol}") from exc
        if not self.is_supported_market(market):
            raise ExchangeRejected(f"{symbol} is not an active USDT linear perpetual")
        tiers = await self.fetch_leverage_tiers(symbol)
        notional = max_notional if max_notional is not None else Decimal(0)
        supported_tier = next(
            (
                tier
                for tier in tiers
                if (
                    tier.max_leverage >= leverage
                    and (notional == 0 or tier.supports(notional, leverage))
                )
            ),
            None,
        )
        if supported_tier is None:
            raise ExchangeRejected(
                f"Binance leverage tiers do not support {leverage}x at notional {notional}"
            )
        if self._demo or self._sandbox:
            # Binance Demo/Testnet does not use the production SAPI restrictions endpoint. The
            # account read and the following isolated/leverage configuration calls validate the
            # credentials against the same USD-M environment as the orders.
            await self._call(lambda: self._client.fetch_balance({"type": "future"}))
        else:
            permissions = await self.fetch_api_permissions()
            if not permissions.can_read or not permissions.can_trade_derivatives:
                raise ExchangeRejected("API key must have read and Binance Futures trading access")
        position_mode = await self._call(self._client.fetch_position_mode)
        if position_mode.get("hedged"):
            raise ExchangeRejected("Binance USD-M account must use one-way position mode")
        positions = await self._call(lambda: self._client.fetch_positions([symbol]))
        if any(Decimal(str(position.get("contracts") or 0)) != 0 for position in positions):
            raise ExchangeRejected(
                f"close the existing {symbol} futures position before starting this bot"
            )
        orders = await self.fetch_open_orders(symbol)
        if orders:
            raise ExchangeRejected(f"cancel existing {symbol} futures orders before starting")

        current_margin = await self._call(lambda: self._client.fetch_margin_mode(symbol))
        if current_margin.get("marginMode") != "isolated":
            await self._call(lambda: self._client.set_margin_mode("isolated", symbol))
        await self._call(lambda: self._client.set_leverage(leverage, symbol))

        configured_margin = await self._call(lambda: self._client.fetch_margin_mode(symbol))
        raw_leverage = (configured_margin.get("info") or {}).get("leverage")
        if configured_margin.get("marginMode") != "isolated":
            raise ExchangeRejected(f"Binance did not confirm isolated margin for {symbol}")
        if raw_leverage is None or int(raw_leverage) != leverage:
            raise ExchangeRejected(f"Binance did not confirm requested {leverage}x leverage")

    def stop_order_type(self, request: StopOrderRequest) -> str:
        if request.product is TradingProduct.LINEAR_PERPETUAL:
            return "market"  # CCXT translates stopPrice into Binance STOP_MARKET/algo order.
        return super().stop_order_type(request)

    def lookup_params(self, client_order_id: str) -> dict[str, Any]:
        if client_order_id.endswith("-sl"):
            # CCXT selects the current USD-M algo-order endpoints with trigger=True.
            return {"clientAlgoId": client_order_id, "trigger": True}
        return super().lookup_params(client_order_id)

    async def fetch_open_orders(self, symbol: str) -> list[VenueOrder]:
        standard = await super().fetch_open_orders(symbol)
        conditional = await self._call(
            lambda: self._client.fetch_open_orders(symbol, None, None, {"trigger": True})
        )
        return [*standard, *conditional]

    def stop_order_params(self, request: StopOrderRequest) -> dict[str, Any]:
        if request.product is not TradingProduct.LINEAR_PERPETUAL:
            return super().stop_order_params(request)
        if not request.reduce_only or request.position_side is None:
            raise ExchangeRejected("Binance USD-M protective stops must reduce a position")
        # CCXT uses this flag to route conditional USD-M orders through Binance's
        # current Algo Order API (POST /fapi/v1/algoOrder). Without it, a
        # stopPrice is translated to the retired conditional-order endpoint.
        return {
            "reduceOnly": True,
            "workingType": "MARK_PRICE",
            "isAlgoOrder": True,
        }

    def market_order_params(self, request: MarketOrderRequest) -> dict[str, Any]:
        return {"reduceOnly": True} if request.reduce_only else {}


def _optional_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ExchangeError("Binance USD-M returned a malformed numeric position field") from None
    if not parsed.is_finite():
        raise ExchangeError("Binance USD-M returned a non-finite position field")
    return parsed


def _positive_decimal(value: Any) -> Decimal | None:
    parsed = _optional_decimal(value)
    return parsed if parsed is not None and parsed > 0 else None


def _optional_integer(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ExchangeError("Binance USD-M returned a malformed leverage field") from None
