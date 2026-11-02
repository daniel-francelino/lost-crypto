from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from modules.bots.domain.models import Bot, BotConfig, BotState, ExecutionMode
from modules.exchanges.domain.models import LeverageTier, MarginMode, TradingProduct
from modules.market_data.domain.models import Candle, Timeframe
from modules.trading.application.parity import _replay_config


def _candles(started: datetime, symbol: str) -> list[Candle]:
    return [
        Candle(
            symbol=symbol,
            timeframe=Timeframe.H1,
            open_time=started,
            open=Decimal("100"),
            high=Decimal("101"),
            low=Decimal("99"),
            close=Decimal("100"),
            volume=Decimal("1"),
        )
    ]


def test_futures_parity_config_preserves_direction_risk_and_pinned_tiers() -> None:
    started = datetime(2024, 1, 1, tzinfo=UTC)
    connection_id = uuid4()
    bot = Bot(
        id=uuid4(),
        config=BotConfig(
            name="Futures parity",
            exchange="binance-usdm",
            strategy_type="mean_reversion_zscore",
            strategy_params={"lookback": 30},
            symbol="BTC/USDT:USDT",
            timeframe=Timeframe.H1,
            initial_capital=Decimal("1000"),
            fee_rate=Decimal("0.0004"),
            slippage_bps=Decimal("2"),
            mode=ExecutionMode.PAPER,
            connection_id=connection_id,
            product=TradingProduct.LINEAR_PERPETUAL,
            leverage=5,
            margin_mode=MarginMode.ISOLATED,
            allow_short=True,
        ),
        desired_state=BotState.RUNNING,
        observed_state=BotState.RUNNING,
        config_version=3,
        created_at=started,
        updated_at=started,
    )
    tiers = (
        LeverageTier(
            tier=1,
            min_notional=Decimal("0"),
            max_notional=Decimal("50000"),
            max_leverage=20,
            maintenance_margin_rate=Decimal("0.004"),
            cumulative_maintenance_amount=Decimal("0"),
        ),
    )

    config = _replay_config(
        bot,
        _candles(started, "BTC/USDT:USDT"),
        started + Timeframe.H1.delta,
        Decimal("900"),
        tiers,
        started,
    )

    assert config.product is TradingProduct.LINEAR_PERPETUAL
    assert config.symbol == "BTC/USDT:USDT"
    assert config.connection_id == connection_id
    assert config.leverage == 5
    assert config.margin_mode is MarginMode.ISOLATED
    assert config.allow_short is True
    assert config.initial_capital == Decimal("900")
    assert config.leverage_tiers == tiers
    assert config.leverage_tiers_at == started


def test_spot_parity_config_keeps_legacy_defaults() -> None:
    started = datetime(2024, 1, 1, tzinfo=UTC)
    bot = Bot(
        id=uuid4(),
        config=BotConfig(
            name="Spot parity",
            strategy_type="mean_reversion_zscore",
            strategy_params={},
            symbol="BTC/USDT",
            timeframe=Timeframe.H1,
            initial_capital=Decimal("1000"),
            fee_rate=Decimal("0.001"),
            slippage_bps=Decimal("0"),
        ),
        desired_state=BotState.RUNNING,
        observed_state=BotState.RUNNING,
        config_version=1,
        created_at=started,
        updated_at=started,
    )

    config = _replay_config(
        bot,
        _candles(started, "BTC/USDT"),
        started + Timeframe.H1.delta,
        Decimal("1000"),
    )

    assert config.product is TradingProduct.SPOT
    assert config.leverage == 1
    assert config.margin_mode is None
    assert config.allow_short is False
    assert config.connection_id is None
    assert config.leverage_tiers == ()
