import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

from core.errors import DomainError
from modules.execution.domain.orders import Fill
from modules.market_data.domain.models import Candle, Timeframe
from modules.strategies.domain.types import Side


class InvalidBacktestConfig(DomainError):
    pass


@dataclass(frozen=True, slots=True)
class BacktestConfig:
    exchange: str
    symbol: str
    timeframe: Timeframe
    start: datetime
    end: datetime
    initial_capital: Decimal
    fee_rate: Decimal  # fraction of notional, charged in the quote asset (0.001 = 0.1%)
    slippage_bps: Decimal  # adverse price move applied to every market fill
    strategy_type: str
    strategy_params: Mapping[str, Any] = field(default_factory=dict)
    seed: int = 0  # recorded for reproducibility; the current fill model is deterministic

    def __post_init__(self) -> None:
        if self.start >= self.end:
            raise InvalidBacktestConfig("start must be before end")
        if self.initial_capital <= 0:
            raise InvalidBacktestConfig("initial_capital must be positive")
        if not (0 <= self.fee_rate < 1):
            raise InvalidBacktestConfig("fee_rate must be in [0, 1)")
        if not (0 <= self.slippage_bps < 10_000):
            raise InvalidBacktestConfig("slippage_bps must be in [0, 10000)")


@dataclass(frozen=True, slots=True)
class EquityPoint:
    time: datetime
    equity: Decimal


@dataclass(frozen=True, slots=True)
class RejectedSignal:
    time: datetime
    side: Side
    reason: str


@dataclass(frozen=True, slots=True)
class BacktestOutcome:
    fills: list[Fill]
    equity_curve: list[EquityPoint]
    rejected: list[RejectedSignal]
    final_cash: Decimal
    final_quantity: Decimal
    first_price: Decimal  # open of the first candle (buy & hold benchmark entry)
    last_price: Decimal  # close of the last candle
    unfilled_signals: int  # signals emitted on the last candle (nothing left to fill them)


def hash_candles(candles: Sequence[Candle]) -> str:
    """Stable fingerprint of the input data, recorded so a run can be reproduced/verified."""

    def num(value: Decimal) -> str:
        return format(value.normalize(), "f")

    digest = hashlib.sha256()
    for c in candles:
        line = (
            f"{c.open_time.isoformat()}|{num(c.open)}|{num(c.high)}|"
            f"{num(c.low)}|{num(c.close)}|{num(c.volume)}\n"
        )
        digest.update(line.encode())
    return digest.hexdigest()
