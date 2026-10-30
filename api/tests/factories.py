from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal

from modules.backtesting.domain.models import BacktestConfig
from modules.market_data.domain.models import Candle, MarketInfo, Timeframe

T0 = datetime(2024, 1, 1, tzinfo=UTC)

MARKET = MarketInfo(
    symbol="BTC/USDT",
    step_size=Decimal("0.001"),
    tick_size=Decimal("0.01"),
    min_quantity=Decimal("0.001"),
    min_notional=Decimal("10"),
)


def make_candles(
    closes: Sequence[int | str],
    opens: Sequence[int | str] | None = None,
    *,
    symbol: str = "BTC/USDT",
    timeframe: Timeframe = Timeframe.H1,
    start: datetime = T0,
) -> list[Candle]:
    """Candles whose open defaults to the previous close (no gaps between candles)."""
    candles: list[Candle] = []
    for i, close in enumerate(closes):
        c = Decimal(close)
        previous_close = Decimal(closes[max(i - 1, 0)])
        o = Decimal(opens[i]) if opens is not None else previous_close
        candles.append(
            Candle(
                symbol=symbol,
                timeframe=timeframe,
                open_time=start + i * timeframe.delta,
                open=o,
                high=max(o, c),
                low=min(o, c),
                close=c,
                volume=Decimal(1),
            )
        )
    return candles


def make_config(
    *,
    fast: int = 2,
    slow: int = 3,
    capital: str = "1000",
    fee_rate: str = "0",
    slippage_bps: str = "0",
    n_candles: int = 100,
) -> BacktestConfig:
    return BacktestConfig(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe=Timeframe.H1,
        start=T0,
        end=T0 + n_candles * Timeframe.H1.delta,
        initial_capital=Decimal(capital),
        fee_rate=Decimal(fee_rate),
        slippage_bps=Decimal(slippage_bps),
        strategy_type="ema_crossover",
        strategy_params={"fast_period": fast, "slow_period": slow},
    )
