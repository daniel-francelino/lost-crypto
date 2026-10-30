"""Simulated market fills, shared by backtest and paper trading so both behave identically."""

from datetime import datetime
from decimal import Decimal

from modules.execution.domain.normalizer import normalize_quantity
from modules.execution.domain.orders import Fill
from modules.market_data.domain.models import MarketInfo
from modules.strategies.domain.types import Side

_BPS = Decimal(10_000)


def slipped_price(side: Side, reference_price: Decimal, slippage_bps: Decimal) -> Decimal:
    """Adverse slippage: buys fill higher, sells fill lower."""
    factor = slippage_bps / _BPS
    return reference_price * (1 + factor) if side is Side.BUY else reference_price * (1 - factor)


def affordable_buy_quantity(
    budget: Decimal, price: Decimal, fee_rate: Decimal, market: MarketInfo
) -> Decimal:
    """Largest valid quantity whose cost *including the fee* fits in ``budget``."""
    return normalize_quantity(budget / (price * (1 + fee_rate)), price, market)


def simulate_market_fill(
    side: Side,
    quantity: Decimal,
    reference_price: Decimal,
    fee_rate: Decimal,
    slippage_bps: Decimal,
    market: MarketInfo,
    time: datetime,
) -> Fill:
    """Fill ``quantity`` at the reference price plus slippage, charging the fee in quote."""
    price = slipped_price(side, reference_price, slippage_bps)
    qty = normalize_quantity(quantity, price, market)
    return Fill(time=time, side=side, quantity=qty, price=price, fee=qty * price * fee_rate)
