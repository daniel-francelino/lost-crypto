from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, Self
from uuid import uuid4

import pytest

from modules.backtesting.domain.models import BacktestConfig, FillTiming
from modules.backtesting.domain.perpetual_engine import run_perpetual_backtest
from modules.exchanges.domain.models import (
    LeverageTier,
    MarginMode,
    TradingProduct,
)
from modules.market_data.domain.models import Candle, FundingRate, MarketInfo, Timeframe
from modules.strategies.domain.base import Strategy, StrategyStyle
from modules.strategies.domain.types import (
    Side,
    Signal,
    SignalKind,
    StrategyContext,
    StrategyResult,
)

T0 = datetime(2024, 1, 1, tzinfo=UTC)


class _EnterOnce(Strategy[int]):
    TYPE_KEY = "test_enter_once"
    NAME = "Test enter once"
    DESCRIPTION = "Enters one position on the first candle."
    STYLE = StrategyStyle.TREND
    PARAMETERS = ()

    @classmethod
    def from_params(cls, params: Mapping[str, Any]) -> Self:
        if params:
            raise ValueError("this test strategy takes no parameters")
        return cls()

    def initial_state(self) -> int:
        return 0

    def evaluate(self, ctx: StrategyContext, state: int) -> StrategyResult[int]:
        if state == 1 and ctx.position_quantity > 0:
            side = Side.SELL if not ctx.is_short else Side.BUY
            return StrategyResult(
                (
                    Signal(
                        side=side,
                        symbol=ctx.symbol,
                        kind=SignalKind.EXIT,
                        reason="test exit",
                    ),
                ),
                state + 1,
            )
        if state:
            return StrategyResult((), state + 1)
        side = Side.SELL if ctx.allow_short else Side.BUY
        return StrategyResult(
            (
                Signal(
                    side=side,
                    symbol=ctx.symbol,
                    kind=SignalKind.ENTRY,
                    reason="test entry",
                ),
            ),
            state + 1,
        )

    def serialize_state(self, state: int) -> dict[str, Any]:
        return {"state": state}

    def deserialize_state(self, raw: dict[str, Any]) -> int:
        return int(raw["state"])


def _candle(at: datetime, *, open_: str, high: str, low: str, close: str) -> Candle:
    return Candle(
        symbol="BTC/USDT:USDT",
        timeframe=Timeframe.H1,
        open_time=at,
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=Decimal(100),
    )


@pytest.mark.parametrize(
    ("allow_short", "open_", "high", "low", "expected"),
    [
        (False, "85", "95", "80", Decimal("85")),
        (True, "115", "120", "105", Decimal("115")),
        (False, "100", "105", "80", Decimal("90") / Decimal("0.995")),
        (True, "100", "120", "95", Decimal("110") / Decimal("1.005")),
    ],
)
def test_liquidation_fill_uses_adverse_open_when_price_gaps_through_threshold(
    allow_short: bool, open_: str, high: str, low: str, expected: Decimal
) -> None:
    symbol = "BTC/USDT:USDT"
    marks = [
        _candle(T0, open_="100", high="100", low="100", close="100"),
        _candle(T0 + Timeframe.H1.delta, open_=open_, high=high, low=low, close="100"),
    ]
    signals = [
        Candle(
            symbol=symbol,
            timeframe=item.timeframe,
            open_time=item.open_time,
            open=item.open,
            high=item.high,
            low=item.low,
            close=item.close,
            volume=item.volume,
        )
        for item in marks
    ]
    config = BacktestConfig(
        exchange="binance-usdm",
        symbol=symbol,
        timeframe=Timeframe.H1,
        start=T0,
        end=T0 + 2 * Timeframe.H1.delta,
        initial_capital=Decimal("1000"),
        fee_rate=Decimal("0"),
        slippage_bps=Decimal("0"),
        strategy_type=_EnterOnce.TYPE_KEY,
        product=TradingProduct.LINEAR_PERPETUAL,
        leverage=10,
        margin_mode=MarginMode.ISOLATED,
        allow_short=allow_short,
        connection_id=uuid4(),
        leverage_tiers=(
            LeverageTier(
                tier=1,
                min_notional=Decimal("0"),
                max_notional=Decimal("1000000"),
                max_leverage=10,
                maintenance_margin_rate=Decimal("0.005"),
            ),
        ),
        fill_timing=FillTiming.SIGNAL_CLOSE,
    )

    result = run_perpetual_backtest(
        config,
        signals,
        marks,
        [],
        MarketInfo(symbol, Decimal("0.001"), Decimal("0.01"), Decimal("0.001"), Decimal("5")),
        _EnterOnce(),
        liquidation_fee_rate=Decimal("0"),
    )

    assert result.liquidation_count == 1
    assert result.final_quantity == 0
    assert result.fills[-1].time == T0 + timedelta(hours=1)
    assert result.fills[-1].price == expected
    assert result.min_liquidation_distance_pct is not None
    assert result.min_liquidation_distance_pct < 0


@pytest.mark.parametrize("allow_short", [False, True])
def test_funding_cash_flow_uses_position_direction_and_event_mark(allow_short: bool) -> None:
    symbol = "BTC/USDT:USDT"
    candles = [
        _candle(T0, open_="100", high="100", low="100", close="100"),
        _candle(T0 + Timeframe.H1.delta, open_="100", high="100", low="100", close="100"),
    ]
    config = BacktestConfig(
        exchange="binance-usdm",
        symbol=symbol,
        timeframe=Timeframe.H1,
        start=T0,
        end=T0 + 2 * Timeframe.H1.delta,
        initial_capital=Decimal("1000"),
        fee_rate=Decimal("0"),
        slippage_bps=Decimal("0"),
        strategy_type=_EnterOnce.TYPE_KEY,
        product=TradingProduct.LINEAR_PERPETUAL,
        leverage=2,
        margin_mode=MarginMode.ISOLATED,
        allow_short=allow_short,
        connection_id=uuid4(),
        leverage_tiers=(
            LeverageTier(
                tier=1,
                min_notional=Decimal("0"),
                max_notional=Decimal("1000000"),
                max_leverage=10,
                maintenance_margin_rate=Decimal("0.005"),
            ),
        ),
        fill_timing=FillTiming.SIGNAL_CLOSE,
    )

    result = run_perpetual_backtest(
        config,
        candles,
        candles,
        [
            FundingRate(
                symbol=symbol,
                rate=Decimal("0.01"),
                funding_time=T0 + timedelta(hours=1, minutes=30),
                mark_price=Decimal("110"),
            )
        ],
        MarketInfo(symbol, Decimal("0.001"), Decimal("0.01"), Decimal("0.001"), Decimal("5")),
        _EnterOnce(),
        liquidation_fee_rate=Decimal("0"),
    )

    if allow_short:
        assert result.funding_received > 0 and result.funding_paid == 0
    else:
        assert result.funding_paid > 0 and result.funding_received == 0


@pytest.mark.parametrize(
    ("allow_short", "exit_price", "profitable"),
    [
        (False, "110", True),
        (False, "90", False),
        (True, "90", True),
        (True, "110", False),
    ],
)
def test_long_and_short_round_trips_mark_pnl_in_the_correct_direction(
    allow_short: bool, exit_price: str, profitable: bool
) -> None:
    symbol = "BTC/USDT:USDT"
    candles = [
        _candle(T0, open_="100", high="100", low="100", close="100"),
        _candle(
            T0 + Timeframe.H1.delta,
            open_="100",
            high=str(max(100, int(exit_price))),
            low=str(min(100, int(exit_price))),
            close=exit_price,
        ),
    ]
    config = BacktestConfig(
        exchange="binance-usdm",
        symbol=symbol,
        timeframe=Timeframe.H1,
        start=T0,
        end=T0 + 2 * Timeframe.H1.delta,
        initial_capital=Decimal("1000"),
        fee_rate=Decimal("0"),
        slippage_bps=Decimal("0"),
        strategy_type=_EnterOnce.TYPE_KEY,
        product=TradingProduct.LINEAR_PERPETUAL,
        leverage=2,
        margin_mode=MarginMode.ISOLATED,
        allow_short=allow_short,
        connection_id=uuid4(),
        leverage_tiers=(
            LeverageTier(
                tier=1,
                min_notional=Decimal("0"),
                max_notional=Decimal("1000000"),
                max_leverage=10,
                maintenance_margin_rate=Decimal("0.005"),
            ),
        ),
        fill_timing=FillTiming.SIGNAL_CLOSE,
    )

    result = run_perpetual_backtest(
        config,
        candles,
        candles,
        [],
        MarketInfo(symbol, Decimal("0.001"), Decimal("0.01"), Decimal("0.001"), Decimal("5")),
        _EnterOnce(),
        liquidation_fee_rate=Decimal("0"),
    )

    assert result.final_quantity == 0
    assert (result.final_cash > config.initial_capital) is profitable
