from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, Self
from uuid import uuid4

import pytest

from modules.analytics.domain.metrics import compute_metrics
from modules.backtesting.domain.cost_ladder import MULTIPLIERS, run_cost_ladder
from modules.backtesting.domain.data_quality import funding_coverage_report
from modules.backtesting.domain.engine import run_backtest
from modules.backtesting.domain.models import BacktestConfig, FillTiming, InvalidBacktestConfig
from modules.backtesting.domain.perpetual_engine import run_perpetual_backtest
from modules.exchanges.domain.models import (
    LeverageTier,
    MarginMode,
    TradingProduct,
)
from modules.market_data.domain.models import Candle, FundingRate, MarketInfo, Timeframe
from modules.risk_management.domain.models import RiskLimits
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


class _EnterAndHold(_EnterOnce):
    TYPE_KEY = "test_enter_and_hold"
    NAME = "Test enter and hold"

    def evaluate(self, ctx: StrategyContext, state: int) -> StrategyResult[int]:
        if state:
            return StrategyResult((), state + 1)
        return StrategyResult(
            (
                Signal(
                    side=Side.BUY,
                    symbol=ctx.symbol,
                    kind=SignalKind.ENTRY,
                    reason="test entry and hold",
                ),
            ),
            state + 1,
        )


class _ExitThenReverse(_EnterOnce):
    TYPE_KEY = "test_exit_then_reverse"
    NAME = "Test exit then reverse"

    def evaluate(self, ctx: StrategyContext, state: int) -> StrategyResult[int]:
        if state == 0:
            return StrategyResult(
                (Signal(Side.BUY, ctx.symbol, SignalKind.ENTRY, "initial long"),), 1
            )
        if state == 1 and ctx.is_long:
            return StrategyResult(
                (
                    Signal(Side.SELL, ctx.symbol, SignalKind.EXIT, "close long"),
                    Signal(Side.SELL, ctx.symbol, SignalKind.ENTRY, "reverse short"),
                ),
                2,
            )
        return StrategyResult((), state + 1)


class _WarmupEntry(Strategy[int]):
    TYPE_KEY = "test_warmup_entry"
    NAME = "Test warmup entry"
    DESCRIPTION = "Enters after four warmup evaluations."
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
        signals = (
            (Signal(Side.BUY, ctx.symbol, SignalKind.ENTRY, "warmed state entry"),)
            if state == 4 and ctx.is_flat
            else ()
        )
        return StrategyResult(signals, state + 1)

    def serialize_state(self, state: int) -> dict[str, Any]:
        return {"state": state}

    def deserialize_state(self, raw: dict[str, Any]) -> int:
        return int(raw["state"])


class _PartialExitOnce(_EnterOnce):
    TYPE_KEY = "test_partial_exit_once"
    NAME = "Test partial exit once"

    def evaluate(self, ctx: StrategyContext, state: int) -> StrategyResult[int]:
        if state == 0:
            side = Side.SELL if ctx.allow_short else Side.BUY
            signal = Signal(
                side,
                ctx.symbol,
                SignalKind.ENTRY,
                "test entry",
                stop_loss=Decimal("110") if ctx.allow_short else Decimal("90"),
                take_profit=Decimal("80") if ctx.allow_short else Decimal("120"),
            )
        elif state == 1 and ctx.position_quantity > 0:
            side = Side.BUY if ctx.is_short else Side.SELL
            signal = Signal(
                side,
                ctx.symbol,
                SignalKind.EXIT,
                "test partial exit",
                exit_fraction=Decimal("0.5"),
            )
        else:
            return StrategyResult((), state + 1)
        return StrategyResult((signal,), state + 1)


class _ProtectedEntry(Strategy[int]):
    TYPE_KEY = "test_protected_entry"
    NAME = "Test protected entry"
    DESCRIPTION = "Enters once with mirrored stop and target levels."
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
        if state:
            return StrategyResult((), state + 1)
        short = ctx.allow_short
        return StrategyResult(
            (
                Signal(
                    side=Side.SELL if short else Side.BUY,
                    symbol=ctx.symbol,
                    kind=SignalKind.ENTRY,
                    reason="test protected entry",
                    stop_loss=Decimal("110") if short else Decimal("90"),
                    take_profit=Decimal("90") if short else Decimal("110"),
                ),
            ),
            state + 1,
        )

    def serialize_state(self, state: int) -> dict[str, Any]:
        return {"state": state}

    def deserialize_state(self, raw: dict[str, Any]) -> int:
        return int(raw["state"])


def _candle(
    at: datetime,
    *,
    open_: str,
    high: str,
    low: str,
    close: str,
    symbol: str = "BTC/USDT:USDT",
) -> Candle:
    return Candle(
        symbol=symbol,
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
    # OHLC marks locate the event inside the bar, not its exact timestamp. The
    # observable and replayable timestamp is the candle close.
    assert result.fills[-1].time == marks[-1].close_time
    assert result.fills[-1].price == expected
    assert result.min_liquidation_distance_pct is not None
    assert result.min_liquidation_distance_pct < 0


def test_mark_price_crossing_into_a_new_maintenance_tier_uses_its_rate() -> None:
    symbol = "BTC/USDT:USDT"
    marks = [
        _candle(T0, open_="100", high="100", low="100", close="100"),
        _candle(
            T0 + Timeframe.H1.delta,
            open_="120",
            high="122",
            low="112",
            close="120",
        ),
    ]
    candles = [
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
        strategy_type=_EnterAndHold.TYPE_KEY,
        product=TradingProduct.LINEAR_PERPETUAL,
        leverage=10,
        margin_mode=MarginMode.ISOLATED,
        connection_id=uuid4(),
        leverage_tiers=(
            LeverageTier(1, Decimal("0"), Decimal("6000"), 10, Decimal("0.001")),
            LeverageTier(2, Decimal("6000"), Decimal("100000"), 5, Decimal("0.2")),
        ),
        risk=RiskLimits(max_position_fraction=Decimal("0.5"), max_daily_loss_pct=None),
        fill_timing=FillTiming.SIGNAL_CLOSE,
    )

    result = run_perpetual_backtest(
        config,
        candles,
        marks,
        [],
        MarketInfo(symbol, Decimal("0.001"), Decimal("0.01"), Decimal("0.001"), Decimal("5")),
        _EnterAndHold(),
        liquidation_fee_rate=Decimal("0"),
    )

    assert result.liquidation_count == 1
    assert result.fills[-1].price == Decimal("112.5")


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
            ),
            FundingRate(
                symbol=symbol,
                rate=Decimal("0.02"),
                funding_time=T0 + timedelta(hours=1, minutes=30),
                mark_price=Decimal("110"),
                rate_type="special",
            ),
        ],
        MarketInfo(symbol, Decimal("0.001"), Decimal("0.01"), Decimal("0.001"), Decimal("5")),
        _EnterOnce(),
        liquidation_fee_rate=Decimal("0"),
    )

    if allow_short:
        assert result.funding_received == Decimal("66") and result.funding_paid == 0
    else:
        assert result.funding_paid == Decimal("66") and result.funding_received == 0


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
    replay = run_perpetual_backtest(
        config,
        candles,
        candles,
        [],
        MarketInfo(symbol, Decimal("0.001"), Decimal("0.01"), Decimal("0.001"), Decimal("5")),
        _EnterOnce(),
        liquidation_fee_rate=Decimal("0"),
    )

    assert replay == result
    assert result.final_quantity == 0
    assert (result.final_cash > config.initial_capital) is profitable


def test_signal_close_replay_warms_strategy_before_the_trading_window() -> None:
    symbol = "BTC/USDT:USDT"
    candles = [
        _candle(
            T0 + index * Timeframe.H1.delta,
            open_="100",
            high="100",
            low="100",
            close="100",
            symbol=symbol,
        )
        for index in range(5)
    ]
    config = BacktestConfig(
        exchange="binance-usdm",
        symbol=symbol,
        timeframe=Timeframe.H1,
        start=T0,
        end=T0 + 5 * Timeframe.H1.delta,
        initial_capital=Decimal("1000"),
        fee_rate=Decimal("0"),
        slippage_bps=Decimal("0"),
        strategy_type=_WarmupEntry.TYPE_KEY,
        product=TradingProduct.LINEAR_PERPETUAL,
        leverage=2,
        margin_mode=MarginMode.ISOLATED,
        connection_id=uuid4(),
        leverage_tiers=(LeverageTier(1, Decimal("0"), Decimal("1000000"), 10, Decimal("0.005")),),
        fill_timing=FillTiming.SIGNAL_CLOSE,
    )

    result = run_perpetual_backtest(
        config,
        candles,
        candles,
        [],
        MarketInfo(symbol, Decimal("0.001"), Decimal("0.01"), Decimal("0.001"), Decimal("5")),
        _WarmupEntry(),
        liquidation_fee_rate=Decimal("0"),
        trade_from=candles[3].close_time,
    )

    assert len(result.signals) == 1
    assert result.signals[0].bar_time == candles[4].open_time
    assert result.fills and result.final_quantity > 0


def test_perpetual_replay_blocks_reverse_entry_after_same_candle_exit() -> None:
    symbol = "BTC/USDT:USDT"
    candles = [
        _candle(T0, open_="100", high="100", low="100", close="100", symbol=symbol),
        _candle(
            T0 + Timeframe.H1.delta,
            open_="100",
            high="101",
            low="99",
            close="100",
            symbol=symbol,
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
        strategy_type=_ExitThenReverse.TYPE_KEY,
        product=TradingProduct.LINEAR_PERPETUAL,
        leverage=2,
        margin_mode=MarginMode.ISOLATED,
        allow_short=True,
        connection_id=uuid4(),
        leverage_tiers=(LeverageTier(1, Decimal("0"), Decimal("1000000"), 10, Decimal("0.005")),),
        fill_timing=FillTiming.SIGNAL_CLOSE,
    )

    result = run_perpetual_backtest(
        config,
        candles,
        candles,
        [],
        MarketInfo(symbol, Decimal("0.001"), Decimal("0.01"), Decimal("0.001"), Decimal("5")),
        _ExitThenReverse(),
        liquidation_fee_rate=Decimal("0"),
    )

    assert result.final_quantity == 0
    assert len(result.fills) == 2
    assert len(result.rejected) == 1
    assert result.rejected[0].reason == "entry after an exit on the same candle is blocked"


@pytest.mark.parametrize("allow_short", [False, True])
def test_futures_cost_ladder_base_level_matches_full_run(allow_short: bool) -> None:
    symbol = "BTC/USDT:USDT"
    candles = [
        _candle(T0, open_="100", high="100", low="100", close="100"),
        _candle(T0 + Timeframe.H1.delta, open_="100", high="110", low="90", close="105"),
    ]
    config = BacktestConfig(
        exchange="binance-usdm",
        symbol=symbol,
        timeframe=Timeframe.H1,
        start=T0,
        end=T0 + 2 * Timeframe.H1.delta,
        initial_capital=Decimal("1000"),
        fee_rate=Decimal("0.001"),
        slippage_bps=Decimal("5"),
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
        cost_sensitivity=True,
    )
    market = MarketInfo(symbol, Decimal("0.001"), Decimal("0.01"), Decimal("0.001"), Decimal("5"))
    ladder = run_cost_ladder(config, candles, market, _EnterOnce, mark_candles=candles)
    outcome = run_perpetual_backtest(
        config,
        candles,
        candles,
        [],
        market,
        _EnterOnce(),
        liquidation_fee_rate=config.fee_rate,
    )
    metrics = compute_metrics(
        initial_capital=config.initial_capital,
        equity_curve=outcome.equity_curve,
        fills=outcome.fills,
        first_price=outcome.first_price,
        last_price=outcome.last_price,
        open_position=outcome.final_quantity > 0,
        rejected_signals=len(outcome.rejected),
        bar=config.timeframe.delta,
        benchmark_prices=[candle.close for candle in candles],
        in_market=outcome.in_market,
    )

    levels = {Decimal(level["multiplier"]): level for level in ladder["levels"]}
    assert list(levels) == list(MULTIPLIERS)
    assert Decimal(levels[Decimal(1)]["net_pnl"]) == metrics.net_pnl
    assert int(levels[Decimal(1)]["liquidation_count"]) == outcome.liquidation_count
    assert Decimal(levels[Decimal(1)]["maximum_notional"]) == outcome.max_notional


@pytest.mark.parametrize("allow_short", [False, True])
def test_futures_partial_exit_closes_only_the_requested_fraction(allow_short: bool) -> None:
    symbol = "BTC/USDT:USDT"
    candles = [
        _candle(T0, open_="100", high="100", low="100", close="100"),
        _candle(T0 + Timeframe.H1.delta, open_="100", high="102", low="98", close="101"),
        _candle(
            T0 + 2 * Timeframe.H1.delta,
            open_="105" if allow_short else "95",
            high="111" if allow_short else "98",
            low="102" if allow_short else "89",
            close="106" if allow_short else "94",
        ),
    ]
    config = BacktestConfig(
        exchange="binance-usdm",
        symbol=symbol,
        timeframe=Timeframe.H1,
        start=T0,
        end=T0 + 3 * Timeframe.H1.delta,
        initial_capital=Decimal("1000"),
        fee_rate=Decimal("0"),
        slippage_bps=Decimal("0"),
        strategy_type=_PartialExitOnce.TYPE_KEY,
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
        _PartialExitOnce(),
        liquidation_fee_rate=Decimal("0"),
    )

    assert result.final_quantity == 0
    assert [fill.quantity for fill in result.fills] == [Decimal("20"), Decimal("10"), Decimal("10")]
    assert result.fills[2].price == (Decimal("110") if allow_short else Decimal("90"))
    assert result.in_market == [True, True, False]


def test_spot_partial_exit_closes_only_the_requested_fraction() -> None:
    symbol = "BTC/USDT"
    candles = [
        _candle(T0, open_="100", high="100", low="100", close="100", symbol=symbol),
        _candle(
            T0 + Timeframe.H1.delta,
            open_="100",
            high="102",
            low="98",
            close="101",
            symbol=symbol,
        ),
    ]
    config = BacktestConfig(
        exchange="binance",
        symbol=symbol,
        timeframe=Timeframe.H1,
        start=T0,
        end=T0 + 2 * Timeframe.H1.delta,
        initial_capital=Decimal("1000"),
        fee_rate=Decimal("0"),
        slippage_bps=Decimal("0"),
        strategy_type=_PartialExitOnce.TYPE_KEY,
        fill_timing=FillTiming.SIGNAL_CLOSE,
    )
    result = run_backtest(
        config,
        candles,
        MarketInfo(symbol, Decimal("0.001"), Decimal("0.01"), Decimal("0.001"), Decimal("5")),
        _PartialExitOnce(),
    )

    assert result.final_quantity == Decimal("5")
    assert [fill.quantity for fill in result.fills] == [Decimal("10"), Decimal("5")]


@pytest.mark.parametrize(
    ("kind", "fraction"),
    [
        (SignalKind.EXIT, Decimal(0)),
        (SignalKind.EXIT, Decimal("1.01")),
        (SignalKind.ENTRY, Decimal("0.5")),
        (SignalKind.EXIT, Decimal("NaN")),
    ],
)
def test_exit_fraction_rejects_invalid_or_non_exit_values(
    kind: SignalKind, fraction: Decimal
) -> None:
    with pytest.raises(ValueError, match="exit_fraction"):
        Signal(Side.SELL, "BTC/USDT", kind, "test", exit_fraction=fraction)


@pytest.mark.parametrize(
    ("allow_short", "open_", "high", "low", "expected_exit"),
    [
        (False, "100", "105", "89", Decimal("90")),
        (False, "85", "95", "80", Decimal("85")),
        (False, "100", "111", "95", Decimal("110")),
        (True, "100", "111", "95", Decimal("110")),
        (True, "115", "120", "105", Decimal("115")),
        (True, "100", "105", "89", Decimal("90")),
    ],
)
def test_futures_stops_targets_and_gaps_exit_at_mirrored_prices(
    allow_short: bool,
    open_: str,
    high: str,
    low: str,
    expected_exit: Decimal,
) -> None:
    symbol = "BTC/USDT:USDT"
    candles = [
        _candle(T0, open_="100", high="100", low="100", close="100"),
        _candle(
            T0 + Timeframe.H1.delta,
            open_=open_,
            high=high,
            low=low,
            close="100",
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
        strategy_type=_ProtectedEntry.TYPE_KEY,
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
        _ProtectedEntry(),
        liquidation_fee_rate=Decimal("0"),
    )

    assert result.final_quantity == 0
    assert result.liquidation_count == 0
    assert len(result.fills) == 2
    assert result.fills[-1].price == expected_exit


@pytest.mark.parametrize(
    "missing", ["mark_candles", "funding_mark", "funding_history", "funding_gap"]
)
def test_perpetual_backtest_refuses_incomplete_auxiliary_data(missing: str) -> None:
    symbol = "BTC/USDT:USDT"
    candle_count = 10 if missing in {"funding_history", "funding_gap"} else 2
    candles = [
        _candle(
            T0 + i * Timeframe.H1.delta,
            open_="100",
            high="101",
            low="99",
            close="100",
        )
        for i in range(candle_count)
    ]
    config = BacktestConfig(
        exchange="binance-usdm",
        symbol=symbol,
        timeframe=Timeframe.H1,
        start=T0,
        end=T0 + candle_count * Timeframe.H1.delta,
        initial_capital=Decimal("1000"),
        fee_rate=Decimal("0"),
        slippage_bps=Decimal("0"),
        strategy_type=_EnterOnce.TYPE_KEY,
        product=TradingProduct.LINEAR_PERPETUAL,
        leverage=2,
        margin_mode=MarginMode.ISOLATED,
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
    funding = (
        [
            FundingRate(
                symbol=symbol,
                rate=Decimal("0.001"),
                funding_time=T0 + timedelta(minutes=30),
                mark_price=None,
            )
        ]
        if missing == "funding_mark"
        else (
            [
                FundingRate(
                    symbol=symbol,
                    rate=Decimal("0.001"),
                    funding_time=T0 + timedelta(hours=1),
                    mark_price=Decimal("100"),
                ),
                FundingRate(
                    symbol=symbol,
                    rate=Decimal("0.001"),
                    funding_time=T0 + timedelta(hours=10),
                    mark_price=Decimal("100"),
                ),
            ]
            if missing == "funding_gap"
            else []
        )
    )
    marks = [] if missing == "mark_candles" else candles

    with pytest.raises(
        InvalidBacktestConfig,
        match=(
            r"complete matching coverage|event-time mark|funding history is missing|"
            r"funding history contains an uncovered interval"
        ),
    ):
        run_perpetual_backtest(
            config,
            candles,
            marks,
            funding,
            MarketInfo(symbol, Decimal("0.001"), Decimal("0.01"), Decimal("0.001"), Decimal("5")),
            _EnterOnce(),
            liquidation_fee_rate=Decimal("0"),
        )


def test_hourly_funding_schedule_is_applied_and_reported_without_certifying_completeness() -> None:
    symbol = "BTC/USDT:USDT"
    candles = [
        _candle(
            T0 + i * Timeframe.H1.delta,
            open_="100",
            high="100",
            low="100",
            close="100",
            symbol=symbol,
        )
        for i in range(10)
    ]
    funding = [
        FundingRate(
            symbol=symbol,
            rate=Decimal("0.0001"),
            funding_time=T0 + i * Timeframe.H1.delta,
            mark_price=Decimal("100"),
        )
        for i in range(1, 11)
    ]
    config = BacktestConfig(
        exchange="binance-usdm",
        symbol=symbol,
        timeframe=Timeframe.H1,
        start=T0,
        end=T0 + 10 * Timeframe.H1.delta,
        initial_capital=Decimal("1000"),
        fee_rate=Decimal("0"),
        slippage_bps=Decimal("0"),
        strategy_type=_EnterAndHold.TYPE_KEY,
        product=TradingProduct.LINEAR_PERPETUAL,
        leverage=2,
        margin_mode=MarginMode.ISOLATED,
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
    outcome = run_perpetual_backtest(
        config,
        candles,
        candles,
        funding,
        MarketInfo(symbol, Decimal("0.001"), Decimal("0.01"), Decimal("0.001"), Decimal("5")),
        _EnterAndHold(),
        liquidation_fee_rate=Decimal("0"),
    )

    coverage = funding_coverage_report(candles, funding)
    assert outcome.funding_paid > 0
    assert coverage["event_count"] == 10
    assert coverage["max_observed_gap_seconds"] == 60 * 60
    assert coverage["status"] == "not_certified"


def test_hourly_funding_gap_is_visible_even_when_it_is_below_the_eight_hour_guard() -> None:
    symbol = "BTC/USDT:USDT"
    candles = [
        _candle(
            T0 + i * Timeframe.H1.delta,
            open_="100",
            high="100",
            low="100",
            close="100",
            symbol=symbol,
        )
        for i in range(10)
    ]
    funding = [
        FundingRate(
            symbol=symbol,
            rate=Decimal("0.0001"),
            funding_time=T0 + i * Timeframe.H1.delta,
            mark_price=Decimal("100"),
        )
        for i in (1, 2, 4, 5, 6, 7, 8, 9)
    ]

    coverage = funding_coverage_report(candles, funding)

    assert coverage["status"] == "not_certified"
    assert coverage["max_observed_gap_seconds"] == 2 * 60 * 60
