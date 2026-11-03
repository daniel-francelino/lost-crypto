from datetime import timedelta

import pytest
from pydantic import ValidationError

from factories import T0
from modules.backtesting.presentation.router import BacktestCreate
from modules.bots.presentation.router import BotCreate
from modules.exchanges.domain.models import TradingProduct


@pytest.mark.parametrize(
    ("schema", "base_payload"),
    [
        (BotCreate, {"name": "legacy bot", "strategy_type": "ema_crossover"}),
        (
            BacktestCreate,
            {
                "strategy_type": "ema_crossover",
                "start": T0,
                "end": T0 + timedelta(days=1),
            },
        ),
    ],
)
def test_futures_entry_points_accept_10x_and_reject_fractional_or_over_cap(
    schema: type[BotCreate] | type[BacktestCreate], base_payload: dict[str, object]
) -> None:
    accepted = schema.model_validate(
        {**base_payload, "product": TradingProduct.LINEAR_PERPETUAL, "leverage": 10}
    )
    assert accepted.leverage == 10

    for leverage in (10.01, 11):
        with pytest.raises(ValidationError):
            schema.model_validate(
                {
                    **base_payload,
                    "product": TradingProduct.LINEAR_PERPETUAL,
                    "leverage": leverage,
                }
            )


def test_legacy_bot_create_defaults_remain_spot_long_only_at_one_x() -> None:
    config = BotCreate.model_validate({"name": "legacy bot", "strategy_type": "ema_crossover"})

    assert config.product is TradingProduct.SPOT
    assert config.leverage == 1
    assert config.margin_mode is None
    assert config.allow_short is False


@pytest.mark.parametrize(
    ("schema", "base_payload"),
    [
        (BotCreate, {"name": "futures bot", "strategy_type": "ema_crossover"}),
        (
            BacktestCreate,
            {
                "strategy_type": "ema_crossover",
                "start": T0,
                "end": T0 + timedelta(days=1),
            },
        ),
    ],
)
def test_futures_entry_points_reject_cross_margin(
    schema: type[BotCreate] | type[BacktestCreate], base_payload: dict[str, object]
) -> None:
    with pytest.raises(ValidationError):
        schema.model_validate(
            {
                **base_payload,
                "product": TradingProduct.LINEAR_PERPETUAL,
                "leverage": 2,
                "margin_mode": "cross",
            }
        )
