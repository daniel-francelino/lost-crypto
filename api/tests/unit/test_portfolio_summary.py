from decimal import Decimal
from uuid import uuid4

from factories import T0
from modules.bots.application.service import BotOverview, summarize
from modules.bots.domain.models import Bot, BotConfig, BotState, ExecutionMode
from modules.market_data.domain.models import Timeframe


def _row(
    symbol: str,
    mode: ExecutionMode,
    equity: str,
    *,
    running: bool = False,
    in_position: bool = False,
) -> tuple[BotOverview, Decimal]:
    config = BotConfig(
        name="b",
        strategy_type="ema_crossover",
        strategy_params={},
        symbol=symbol,
        timeframe=Timeframe.H1,
        initial_capital=Decimal(1000),
        fee_rate=Decimal("0.001"),
        slippage_bps=Decimal(5),
        mode=mode,
        connection_id=uuid4() if mode.uses_exchange else None,
    )
    state = BotState.RUNNING if running else BotState.STOPPED
    bot = Bot(uuid4(), config, state, state, 1, T0, T0)
    overview = BotOverview(
        bot=bot,
        equity=Decimal(equity),
        return_pct=Decimal(0),
        realized_pnl=Decimal(equity) - 1000,
        fees_paid=Decimal(2),
        in_position=in_position,
        last_price=None,
    )
    return overview, Decimal(1000)


def test_totals_are_grouped_by_mode_and_quote_currency_and_never_mixed() -> None:
    groups = summarize(
        [
            _row("BTC/USDT", ExecutionMode.PAPER, "1100", running=True, in_position=True),
            _row("ETH/USDT", ExecutionMode.PAPER, "900"),
            _row("BTC/EUR", ExecutionMode.PAPER, "1000"),
            _row("BTC/USDT", ExecutionMode.TESTNET, "1000"),
        ]
    )
    by_key = {(g.mode, g.quote_currency): g for g in groups}
    assert set(by_key) == {
        (ExecutionMode.PAPER, "USDT"),
        (ExecutionMode.PAPER, "EUR"),
        (ExecutionMode.TESTNET, "USDT"),
    }
    usdt = by_key[(ExecutionMode.PAPER, "USDT")]
    assert (usdt.bots, usdt.running, usdt.open_positions) == (2, 1, 1)
    assert usdt.initial_capital == 2000 and usdt.equity == 2000
    assert usdt.realized_pnl == 0 and usdt.fees_paid == 4
    assert usdt.return_pct == 0
    assert by_key[(ExecutionMode.PAPER, "EUR")].bots == 1


def test_return_is_computed_from_the_totals_not_averaged() -> None:
    (group,) = summarize([_row("BTC/USDT", ExecutionMode.PAPER, "1500")])
    assert group.return_pct == Decimal(50)
    assert summarize([]) == []
