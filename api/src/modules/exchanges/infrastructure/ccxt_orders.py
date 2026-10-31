"""Translating CCXT order/trade dicts into our value objects (pure functions).

Everything the system knows about an order on an exchange passes through here, so the
mapping is one small, heavily tested place. CCXT's unified shapes are used; Binance's raw
``info.fills`` (returned by market orders) is accepted as a fallback.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from modules.exchanges.application.ports import Balance, VenueOrder
from modules.exchanges.errors import ExchangeError, UnsupportedFeeAsset
from modules.execution.domain.orders import Fill, OrderStatus
from modules.strategies.domain.types import Side

_STATUS = {
    "open": OrderStatus.OPEN,
    "closed": OrderStatus.FILLED,
    "canceled": OrderStatus.CANCELED,
    "expired": OrderStatus.EXPIRED,
    "rejected": OrderStatus.REJECTED,
}


def _dec(value: Any, default: str = "0") -> Decimal:
    return Decimal(str(value)) if value not in (None, "") else Decimal(default)


def _when(milliseconds: Any, fallback: datetime) -> datetime:
    return datetime.fromtimestamp(int(milliseconds) / 1000, UTC) if milliseconds else fallback


def raw_fills_as_trades(raw_fills: list[dict[str, Any]], quote: str) -> list[dict[str, Any]]:
    """Binance ``fills`` (price, qty, commission, commissionAsset, tradeId) as CCXT trades."""
    return [
        {
            "id": str(f.get("tradeId")) if f.get("tradeId") is not None else None,
            "price": f["price"],
            "amount": f["qty"],
            "fee": {"cost": f.get("commission"), "currency": f.get("commissionAsset") or quote},
            "timestamp": None,
        }
        for f in raw_fills
    ]


def parse_fills(
    trades: list[dict[str, Any]], symbol: str, side: Side, fallback_time: datetime
) -> tuple[Fill, ...]:
    """CCXT trades -> fills, splitting the fee into quote-denominated and base-denominated."""
    base, _, quote = symbol.partition("/")
    fills: list[Fill] = []
    for trade in trades:
        fee_quote = fee_base = Decimal(0)
        fee = trade.get("fee") or {}
        cost, currency = _dec(fee.get("cost")), fee.get("currency")
        if cost:
            if currency == quote:
                fee_quote = cost
            elif currency == base:
                fee_base = cost
            else:
                raise UnsupportedFeeAsset(
                    f"fee charged in {currency}; only {base} and {quote} fees can be valued"
                )
        fills.append(
            Fill(
                time=_when(trade.get("timestamp"), fallback_time),
                side=side,
                quantity=_dec(trade["amount"]),
                price=_dec(trade["price"]),
                fee=fee_quote,
                fee_base=fee_base,
                trade_id=str(trade["id"]) if trade.get("id") is not None else None,
            )
        )
    return tuple(fills)


def parse_order(
    raw: dict[str, Any],
    symbol: str,
    trades: list[dict[str, Any]] | None = None,
    now: datetime | None = None,
) -> VenueOrder:
    """A CCXT order dict -> ``VenueOrder``. ``trades`` overrides the order's embedded fills."""
    info = raw.get("info") or {}
    side = Side(str(raw["side"]).lower())
    quote = symbol.partition("/")[2]
    moment = _when(raw.get("lastTradeTimestamp") or raw.get("timestamp"), now or datetime.now(UTC))

    if trades is None:
        trades = raw.get("trades") or raw_fills_as_trades(info.get("fills") or [], quote)
    fills = parse_fills(trades, symbol, side, moment)

    status_text = str(raw.get("status") or "").lower()
    if status_text not in _STATUS:
        raise ExchangeError(f"unexpected order status from exchange: {raw.get('status')!r}")
    filled = _dec(raw.get("filled"))
    status = _STATUS[status_text]
    if status is OrderStatus.OPEN and filled > 0:
        status = OrderStatus.PARTIALLY_FILLED
    order_type = str(raw.get("type") or "market").lower()
    stop = raw.get("stopPrice") or info.get("stopPrice")
    return VenueOrder(
        client_order_id=str(raw.get("clientOrderId") or info.get("clientOrderId") or ""),
        exchange_order_id=str(raw["id"]) if raw.get("id") is not None else None,
        symbol=symbol,
        side=side,
        quantity=_dec(raw.get("amount")),
        status=status,
        filled_quantity=filled,
        fills=fills,
        order_type="stop_loss" if "stop" in order_type else "market",
        stop_price=_dec(stop) if stop not in (None, "", 0, "0", "0.00000000") else None,
    )


def parse_balances(raw: dict[str, Any]) -> dict[str, Balance]:
    """``fetch_balance`` -> {asset: Balance}, keeping only assets with something in them."""
    balances: dict[str, Balance] = {}
    for asset, total in (raw.get("total") or {}).items():
        if not _dec(total):
            continue
        free = _dec((raw.get("free") or {}).get(asset))
        used = _dec((raw.get("used") or {}).get(asset))
        balances[asset] = Balance(asset, free, used)
    return balances
