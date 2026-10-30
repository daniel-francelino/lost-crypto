from decimal import Decimal

from core.errors import DomainError
from core.money import round_down_to_step
from modules.market_data.domain.models import MarketInfo


class OrderRejected(DomainError):
    """The order violates the exchange's trading rules."""


def normalize_quantity(quantity: Decimal, price: Decimal, market: MarketInfo) -> Decimal:
    """Round the quantity *down* to the lot size and enforce exchange minimums.

    The same rules apply in every execution mode, so an order that would be rejected live is
    rejected in backtest/paper as well.
    """
    normalized = round_down_to_step(quantity, market.step_size)
    if normalized <= 0 or normalized < market.min_quantity:
        raise OrderRejected(
            f"quantity {normalized} is below the minimum quantity {market.min_quantity}"
        )
    notional = normalized * price
    if notional < market.min_notional:
        raise OrderRejected(f"notional {notional} is below the minimum {market.min_notional}")
    return normalized


def round_price(price: Decimal, market: MarketInfo) -> Decimal:
    return round_down_to_step(price, market.tick_size)
