"""Out-of-sample evaluation: the same run, reported separately for its train and test parts.

The strategy runs once over all candles (so its state carries over); metrics are then computed
for the first ``1 - test_fraction`` of the series (train) and the rest (test). A strategy tuned
on the train part that looks good only there is overfit: judge it by the test part.
"""

from collections.abc import Sequence
from decimal import Decimal
from typing import Any

from modules.analytics.domain.metrics import compute_metrics
from modules.backtesting.domain.models import (
    BacktestConfig,
    BacktestOutcome,
    InvalidBacktestConfig,
)
from modules.execution.domain.orders import Fill
from modules.market_data.domain.models import Candle
from modules.strategies.domain.types import Side

MIN_SEGMENT_CANDLES = 2


def _holds_position(fills: Sequence[Fill]) -> bool:
    net = sum((f.quantity if f.side is Side.BUY else -f.quantity for f in fills), Decimal(0))
    return net > 0


def compute_segments(
    config: BacktestConfig, candles: Sequence[Candle], outcome: BacktestOutcome
) -> dict[str, Any] | None:
    fraction = config.test_fraction
    if fraction is None:
        return None
    split = int(Decimal(len(candles)) * (1 - fraction))
    if split < MIN_SEGMENT_CANDLES or len(candles) - split < MIN_SEGMENT_CANDLES:
        raise InvalidBacktestConfig("not enough candles for the requested train/test split")

    split_time = candles[split].open_time
    train_fills = [f for f in outcome.fills if f.time < split_time]
    test_fills = [f for f in outcome.fills if f.time >= split_time]
    rejected_train = sum(1 for r in outcome.rejected if r.time < split_time)

    train = compute_metrics(
        initial_capital=config.initial_capital,
        equity_curve=outcome.equity_curve[:split],
        fills=train_fills,
        first_price=candles[0].open,
        last_price=candles[split - 1].close,
        open_position=_holds_position(train_fills),
        rejected_signals=rejected_train,
    )
    test = compute_metrics(
        initial_capital=outcome.equity_curve[split - 1].equity,  # where the test part begins
        equity_curve=outcome.equity_curve[split:],
        fills=test_fills,
        first_price=candles[split].open,
        last_price=candles[-1].close,
        open_position=outcome.final_quantity > 0,
        rejected_signals=len(outcome.rejected) - rejected_train,
    )
    return {
        "split_at": split_time.isoformat(),
        "test_fraction": str(fraction),
        "train": train.to_dict(),
        "test": test.to_dict(),
    }
