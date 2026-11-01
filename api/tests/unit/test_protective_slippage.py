"""Book 2 ch. 8, O4: alert when a protective exit fills far worse than the configured slippage."""

from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from factories import T0
from modules.bots.domain.models import Bot, BotConfig, BotState, ExecutionMode
from modules.execution.domain.orders import Order, OrderStatus
from modules.market_data.domain.models import Timeframe
from modules.notifications.application.conditions import protective_slippage
from modules.notifications.application.service import WORKER_SCOPE
from modules.notifications.domain.models import AlertKind, AlertSeverity
from modules.strategies.domain.types import Side

D = Decimal
NOW = T0 + timedelta(hours=100)
WINDOW = timedelta(hours=24)


def _bot(slippage: str = "5", mode: ExecutionMode = ExecutionMode.PAPER) -> Bot:
    config = BotConfig(
        name="b",
        strategy_type="ema_crossover",
        strategy_params={},
        symbol="BTC/USDT",
        timeframe=Timeframe.H1,
        initial_capital=D(1000),
        fee_rate=D("0.001"),
        slippage_bps=D(slippage),
        mode=mode,
        connection_id=uuid4() if mode.uses_exchange else None,
    )
    return Bot(uuid4(), config, BotState.RUNNING, BotState.RUNNING, 1, T0, T0)


def _order(
    bot: Bot,
    fill: str,
    *,
    kind: str = "stop_loss",
    status: OrderStatus = OrderStatus.FILLED,
    age_hours: float = 1,
    side: Side = Side.SELL,
) -> Order:
    return Order(
        id=uuid4(),
        bot_id=bot.id,
        session_id=uuid4(),
        client_order_id=uuid4().hex,
        symbol="BTC/USDT",
        side=side,
        quantity=D(1),
        bar_time=T0,
        created_at=T0,
        status=status,
        avg_fill_price=D(fill),
        order_type=kind,
        reference_price=D(100),
        first_fill_at=NOW - timedelta(hours=age_hours),
    )


def _fire(bot: Bot, *orders: Order, multiple: str = "3"):
    return protective_slippage([(bot, list(orders))], NOW, WINDOW, D(multiple))


def test_a_stop_that_filled_far_below_the_reference_raises_a_stable_warning():
    bot = _bot("5")  # limit: max(5, 10 floor) x 3 = 30 bps; a fill at 99.5 is 50 bps worse
    [first] = _fire(bot, _order(bot, "99.5"))
    [again] = _fire(bot, _order(bot, "99.4"))
    assert first.kind is AlertKind.PROTECTIVE_EXIT_SLIPPAGE
    assert first.dedupe_key == f"protective_exit_slippage:{bot.id}" and first.bot_id == bot.id
    assert first.message == again.message  # a worse fill does not rewrite the message
    assert not any(char.isdigit() for char in first.message)
    assert first.severity is AlertSeverity.WARNING


def test_a_fill_inside_the_tolerated_multiple_raises_nothing():
    bot = _bot("20")  # limit 60 bps; 99.5 is 50 bps
    assert _fire(bot, _order(bot, "99.5")) == []


def test_a_bot_with_no_configured_slippage_still_tolerates_a_floor():
    bot = _bot("0")  # floor 10 bps x 3 = 30
    assert _fire(bot, _order(bot, "99.8")) == []  # 20 bps
    assert len(_fire(bot, _order(bot, "99.5"))) == 1  # 50 bps


def test_only_filled_protective_orders_inside_the_window_count():
    bot = _bot()
    bad = "98"
    assert _fire(bot, _order(bot, bad, kind="market")) == []  # not a protective order
    assert _fire(bot, _order(bot, bad, status=OrderStatus.REJECTED)) == []
    assert _fire(bot, _order(bot, bad, age_hours=30)) == []  # older than the window
    assert len(_fire(bot, _order(bot, bad, age_hours=23))) == 1


def test_a_better_than_reference_fill_is_not_slippage():
    bot = _bot()
    assert _fire(bot, _order(bot, "101")) == []


def test_a_live_bot_is_critical_and_each_bot_gets_its_own_alert():
    live, paper = _bot(mode=ExecutionMode.LIVE), _bot()
    out = protective_slippage(
        [(live, [_order(live, "98")]), (paper, [_order(paper, "98")]), (_bot(), [])],
        NOW,
        WINDOW,
        D(3),
    )
    assert {c.severity for c in out} == {AlertSeverity.CRITICAL, AlertSeverity.WARNING}
    assert len({c.dedupe_key for c in out}) == 2


def test_the_worker_watches_this_kind():
    assert AlertKind.PROTECTIVE_EXIT_SLIPPAGE in WORKER_SCOPE
