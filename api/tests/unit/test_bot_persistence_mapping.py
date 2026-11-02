from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from modules.bots.domain.changes import config_changes
from modules.bots.domain.models import BotConfig, BotState
from modules.bots.infrastructure.orm import BotRow
from modules.bots.infrastructure.repository import _config_values, _to_bot
from modules.exchanges.domain.models import MarginMode, TradingProduct
from modules.market_data.domain.models import Timeframe
from modules.risk_management.domain.models import RiskLimits


def _round_trip(config: BotConfig) -> BotConfig:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    values = _config_values(config)
    row = BotRow(
        id=uuid4(),
        desired_state=BotState.STOPPED.value,
        observed_state=BotState.STOPPED.value,
        config_version=1,
        created_at=now,
        updated_at=now,
        last_heartbeat_at=None,
        last_error=None,
        live_approved_config_version=None,
        live_approved_at=None,
        **values,
    )

    return _to_bot(row).config


@pytest.mark.parametrize(
    ("config", "expected_product", "expected_leverage", "expected_margin", "expected_short"),
    [
        (
            BotConfig(
                name="legacy-spot",
                strategy_type="ema_crossover",
                strategy_params={},
                symbol="BTC/USDT",
                timeframe=Timeframe.H1,
                initial_capital=Decimal("1000"),
                fee_rate=Decimal("0.001"),
                slippage_bps=Decimal("2"),
            ),
            TradingProduct.SPOT,
            1,
            None,
            False,
        ),
        (
            BotConfig(
                name="demo-futures",
                exchange="binance-usdm",
                strategy_type="ema_crossover",
                strategy_params={},
                symbol="BTC/USDT:USDT",
                timeframe=Timeframe.H1,
                initial_capital=Decimal("1000"),
                fee_rate=Decimal("0.0005"),
                slippage_bps=Decimal("2"),
                connection_id=uuid4(),
                product=TradingProduct.LINEAR_PERPETUAL,
                leverage=7,
                margin_mode=MarginMode.ISOLATED,
                allow_short=True,
                risk=RiskLimits(min_liquidation_distance_pct=Decimal("8")),
            ),
            TradingProduct.LINEAR_PERPETUAL,
            7,
            MarginMode.ISOLATED,
            True,
        ),
    ],
)
def test_bot_configuration_repository_mapping_round_trips_spot_and_futures(
    config: BotConfig,
    expected_product: TradingProduct,
    expected_leverage: int,
    expected_margin: MarginMode | None,
    expected_short: bool,
) -> None:
    restored = _round_trip(config)

    assert restored == config
    assert restored.product is expected_product
    assert restored.leverage == expected_leverage
    assert restored.margin_mode is expected_margin
    assert restored.allow_short is expected_short


def test_futures_risk_fields_are_in_config_changes_and_invalidate_approval_version() -> None:
    spot = BotConfig(
        name="bot",
        strategy_type="ema_crossover",
        strategy_params={},
        symbol="BTC/USDT",
        timeframe=Timeframe.H1,
        initial_capital=Decimal("1000"),
        fee_rate=Decimal("0.001"),
        slippage_bps=Decimal("2"),
    )
    futures = BotConfig(
        name="bot",
        exchange="binance-usdm",
        strategy_type="ema_crossover",
        strategy_params={},
        symbol="BTC/USDT:USDT",
        timeframe=Timeframe.H1,
        initial_capital=Decimal("1000"),
        fee_rate=Decimal("0.0005"),
        slippage_bps=Decimal("2"),
        connection_id=uuid4(),
        product=TradingProduct.LINEAR_PERPETUAL,
        leverage=4,
        margin_mode=MarginMode.ISOLATED,
        allow_short=True,
    )

    changes = config_changes(spot, futures)

    assert {"product", "leverage", "margin_mode", "allow_short"} <= changes.keys()

