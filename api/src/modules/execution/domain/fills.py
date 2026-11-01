"""Simulated market fills, shared by backtest and paper trading so both behave identically."""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from modules.execution.domain.normalizer import normalize_quantity
from modules.execution.domain.orders import Fill
from modules.market_data.domain.models import Candle, MarketInfo
from modules.strategies.domain.types import Side

_BPS = Decimal(10_000)
MAX_SLIPPAGE_BPS = Decimal(9_999)


class SlippageModel(StrEnum):
    """How the backtest prices slippage. ``fixed`` is one number per run (and what the paper
    trader uses); ``volatility_size`` adds to it with the candle's range and the order's size
    against the candle's traded value (book 2 ch. 7, O2)."""

    FIXED = "fixed"
    VOLATILITY_SIZE = "volatility_size"


def effective_slippage_bps(
    model: SlippageModel,
    base_bps: Decimal,
    k_range: Decimal,
    k_size: Decimal,
    candle: Candle,
    notional: Decimal,
) -> Decimal:
    """Slippage in bps for one fill. Never below ``base_bps`` (the extra cost only worsens the
    fill). ``fixed`` returns ``base_bps`` untouched, so results do not change.

    * range term: ``k_range`` x the candle's range in bps, ``(high - low) / open``;
    * size term: ``k_size`` x the order's share of the candle's traded value in bps, with the
      traded value approximated as ``volume x close``; zero when the candle has no volume.
    """
    if model is SlippageModel.FIXED:
        return base_bps
    range_bps = (candle.high - candle.low) / candle.open * _BPS if candle.open > 0 else Decimal(0)
    traded = candle.volume * candle.close
    size_bps = notional / traded * _BPS if traded > 0 else Decimal(0)
    return min(base_bps + k_range * range_bps + k_size * size_bps, MAX_SLIPPAGE_BPS)


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
