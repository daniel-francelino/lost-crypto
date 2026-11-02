from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from core.errors import ConflictError
from modules.bots.domain.models import Bot, BotConfig, BotState, ExecutionMode
from modules.exchanges.domain.models import LeverageTier, MarginMode, TradingProduct
from modules.market_data.domain.models import Timeframe
from modules.trading.application.perpetual_paper import PerpetualPaperTrader, _tier_for

D = Decimal


def _tiers() -> list[LeverageTier]:
    return [
        LeverageTier(1, D("0"), D("50000"), 20, D("0.005")),
        LeverageTier(2, D("50000"), D("1000000"), 5, D("0.01")),
    ]


def _bot() -> Bot:
    now = datetime(2024, 1, 1, tzinfo=UTC)
    config = BotConfig(
        name="Tier test",
        exchange="binance-usdm",
        strategy_type="ema_crossover",
        strategy_params={},
        symbol="BTC/USDT:USDT",
        timeframe=Timeframe.H1,
        initial_capital=D("1000"),
        fee_rate=D("0.0005"),
        slippage_bps=D("0"),
        mode=ExecutionMode.PAPER,
        connection_id=uuid4(),
        product=TradingProduct.LINEAR_PERPETUAL,
        leverage=10,
        margin_mode=MarginMode.ISOLATED,
    )
    return Bot(uuid4(), config, BotState.RUNNING, BotState.RUNNING, 1, now, now)


class _Exchange:
    async def fetch_leverage_tiers(self, symbol: str) -> list[LeverageTier]:
        assert symbol == "BTC/USDT:USDT"
        return _tiers()


class _Resolver:
    async def exchange_for(self, connection_id) -> _Exchange:
        return _Exchange()


@pytest.mark.asyncio
async def test_paper_trader_keeps_maintenance_tiers_beyond_entry_leverage_limit() -> None:
    bot = _bot()
    trader = PerpetualPaperTrader(
        stores=None,  # type: ignore[arg-type]
        strategies=None,  # type: ignore[arg-type]
        exchanges=None,  # type: ignore[arg-type]
        resolver=_Resolver(),  # type: ignore[arg-type]
        clock=None,  # type: ignore[arg-type]
        ids=None,  # type: ignore[arg-type]
    )

    tiers = await trader._leverage_tiers(bot, datetime(2024, 1, 1, tzinfo=UTC))

    assert tiers == _tiers()
    # A position can appreciate into a higher maintenance bracket even though that bracket
    # would not allow a new 10x entry at the larger notional.
    assert _tier_for(tiers, D("49999.99")).tier == 1
    assert _tier_for(tiers, D("50000")).tier == 2
    assert _tier_for(tiers, D("60000")).tier == 2
    with pytest.raises(
        ConflictError, match="no Binance leverage tier covers notional 60000 at 10x"
    ):
        _tier_for(tiers, D("60000"), leverage=10)
