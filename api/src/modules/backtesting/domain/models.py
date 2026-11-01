import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from core.errors import DomainError
from modules.execution.domain.fills import SlippageModel
from modules.execution.domain.orders import Fill
from modules.market_data.domain.models import Candle, Timeframe
from modules.risk_management.domain.models import RiskLimits
from modules.strategies.domain.types import Side, SignalKind


class InvalidBacktestConfig(DomainError):
    pass


class FillTiming(StrEnum):
    """When a signal is filled (book 1 ch. 5): at the next candle's open (the backtest's
    default), or at the close of the signal candle, which is what the bots do."""

    NEXT_OPEN = "next_open"
    SIGNAL_CLOSE = "signal_close"


MAX_COST_MULTIPLIER = 3  # the highest level of the cost ladder (``domain.cost_ladder``)


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
    test_fraction: Decimal | None = None  # share of the series (at the end) held out as test
    cost_sensitivity: bool = False  # also re-run at several cost levels (cost ladder)
    # The operator's drawdown tolerance (book 1 ch. 2, C6): results that exceed it are flagged.
    max_drawdown_tolerance_pct: Decimal | None = None
    max_drawdown_tolerance_days: int | None = None
    allow_gaps: bool = False  # run even when the range misses many candles (book 1 ch. 3, O4)
    fill_timing: FillTiming = FillTiming.NEXT_OPEN
    # The bot's risk module inside the backtest (sizing and pauses); None = all-in sizing.
    risk: RiskLimits | None = None
    # Slippage model (book 2 ch. 7, O2): ``fixed`` keeps one number per run; the other adds terms
    # that grow with the candle's range and with the order's size against its traded value.
    slippage_model: SlippageModel = SlippageModel.FIXED
    slippage_k_range: Decimal = Decimal(0)
    slippage_k_size: Decimal = Decimal(0)

    def __post_init__(self) -> None:
        if self.start >= self.end:
            raise InvalidBacktestConfig("start must be before end")
        if self.initial_capital <= 0:
            raise InvalidBacktestConfig("initial_capital must be positive")
        if not (0 <= self.fee_rate < 1):
            raise InvalidBacktestConfig("fee_rate must be in [0, 1)")
        if not (0 <= self.slippage_bps < 10_000):
            raise InvalidBacktestConfig("slippage_bps must be in [0, 10000)")
        if self.slippage_k_range < 0 or self.slippage_k_size < 0:
            raise InvalidBacktestConfig("slippage coefficients must not be negative")
        if self.test_fraction is not None and not (0 < self.test_fraction < 1):
            raise InvalidBacktestConfig("test_fraction must be between 0 and 1 (exclusive)")
        if self.cost_sensitivity:
            if self.fee_rate == 0 and self.slippage_bps == 0:
                raise InvalidBacktestConfig("cost sensitivity needs a non-zero fee or slippage")
            if self.fee_rate * MAX_COST_MULTIPLIER >= 1 or (
                self.slippage_bps * MAX_COST_MULTIPLIER >= 10_000
            ):
                raise InvalidBacktestConfig("costs too high to be tripled for the cost ladder")
        tolerance = self.max_drawdown_tolerance_pct
        if tolerance is not None and not (0 < tolerance <= 100):
            raise InvalidBacktestConfig("max_drawdown_tolerance_pct must be in (0, 100]")
        days = self.max_drawdown_tolerance_days
        if days is not None and days <= 0:
            raise InvalidBacktestConfig("max_drawdown_tolerance_days must be positive")


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
class EmittedSignal:
    """A signal the strategy emitted, keyed by its candle (compared with a bot's signals)."""

    bar_time: datetime
    side: Side
    kind: SignalKind


@dataclass(frozen=True, slots=True)
class BacktestOutcome:
    fills: list[Fill]
    equity_curve: list[EquityPoint]
    in_market: list[bool]  # aligned with equity_curve: a position was held at that close
    rejected: list[RejectedSignal]
    final_cash: Decimal
    final_quantity: Decimal
    first_price: Decimal  # open of the first candle (buy & hold benchmark entry)
    last_price: Decimal  # close of the last candle
    unfilled_signals: int  # signals emitted on the last candle (nothing left to fill them)
    signals: list[EmittedSignal] = field(default_factory=list)
    paused: tuple[datetime, str] | None = None  # when the risk guard paused it, and why
    sizing: str = "all_in"  # "all_in" | "risk_limits"


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
