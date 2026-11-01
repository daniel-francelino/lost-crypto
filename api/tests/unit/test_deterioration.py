"""Book 2 ch. 4, O1: the monitor that warns when a bot leaves its backtest's range."""

from datetime import timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from factories import T0
from modules.bots.domain.models import Bot, BotConfig, BotState, ExecutionMode
from modules.market_data.domain.models import Timeframe
from modules.notifications.application.service import AlertMonitor
from modules.notifications.domain.models import AlertKind, AlertSeverity, Condition
from modules.trading.application.comparison import RealizedVsBacktest
from modules.trading.application.deterioration import DeteriorationWatch
from modules.trading.domain.comparison import MIN_PERIODS, compare_sharpe
from modules.trading.domain.deterioration import deterioration

D = Decimal


def _comparison(realized: str, backtest: str, periods: int):
    return compare_sharpe(D(realized), D(backtest), periods)


def test_sharpe_below_half_with_a_real_sample_is_flagged():
    found = deterioration(_comparison("0.8", "2", 100), D(2), D(10))
    assert found is not None and found.sharpe_below_half and not found.drawdown_above_backtest


def test_exactly_half_is_still_acceptable():
    assert deterioration(_comparison("1", "2", 100), D(2), D(10)) is None


def test_a_drawdown_deeper_than_the_backtests_is_flagged_even_with_a_good_sharpe():
    found = deterioration(_comparison("2", "2", 100), D(12), D(10))
    assert found is not None and found.drawdown_above_backtest and not found.sharpe_below_half


def test_both_signals_can_fire_together():
    found = deterioration(_comparison("0.1", "2", 100), D(30), D(10))
    assert found is not None and found.sharpe_below_half and found.drawdown_above_backtest


def test_a_short_live_sample_never_flags_anything():
    comparison = _comparison("0.1", "2", MIN_PERIODS - 1)
    assert deterioration(comparison, D(90), D(10)) is None


def test_a_backtest_without_a_positive_sharpe_can_still_flag_the_drawdown_only():
    found = deterioration(_comparison("1", "0", 100), D(20), D(10))
    assert found is not None and found.drawdown_above_backtest and not found.sharpe_below_half


def test_missing_drawdowns_flag_nothing_and_a_zero_backtest_drawdown_is_not_a_baseline():
    assert deterioration(_comparison("2", "2", 100), None, D(10)) is None
    assert deterioration(_comparison("2", "2", 100), D(5), None) is None
    assert deterioration(_comparison("2", "2", 100), D(5), D(0)) is None


def _bot(state: BotState = BotState.RUNNING) -> Bot:
    config = BotConfig(
        name="b",
        strategy_type="ema_crossover",
        strategy_params={},
        symbol="BTC/USDT",
        timeframe=Timeframe.H1,
        initial_capital=D(1000),
        fee_rate=D("0.001"),
        slippage_bps=D(5),
        mode=ExecutionMode.PAPER,
    )
    return Bot(uuid4(), config, state, state, 1, T0, T0)


class FakeComparator:
    def __init__(self, results: dict[UUID, RealizedVsBacktest | Exception]) -> None:
        self.results = results
        self.calls = 0

    async def compare(self, bot_id: UUID, run_id: UUID | None = None) -> RealizedVsBacktest:
        self.calls += 1
        result = self.results[bot_id]
        if isinstance(result, Exception):
            raise result
        return result


def _result(realized: str, backtest: str, drawdown: str = "1", max_dd: str = "10"):
    return RealizedVsBacktest(
        uuid4(),
        T0,
        _comparison(realized, backtest, 100),
        D(5),
        None,
        D(drawdown),
        D(max_dd),
    )


async def test_watch_turns_a_deteriorated_running_bot_into_a_stable_warning():
    bot = _bot()
    watch = DeteriorationWatch(FakeComparator({bot.id: _result("0.5", "2")}))
    [first] = await watch.conditions([bot])
    [again] = await watch.conditions([bot])
    assert first.kind is AlertKind.PERFORMANCE_DEGRADED
    assert first.severity is AlertSeverity.WARNING
    assert first.dedupe_key == f"performance_degraded:{bot.id}" and first.bot_id == bot.id
    assert first.message == again.message and "Sharpe real abaixo de metade" in first.message
    assert any(char.isdigit() for char in first.message) is False  # nothing that changes per check


async def test_watch_ignores_stopped_bots_healthy_bots_and_failures():
    stopped, healthy, broken = _bot(BotState.STOPPED), _bot(), _bot()
    comparator = FakeComparator(
        {
            stopped.id: _result("0.1", "2"),
            healthy.id: _result("2", "2"),
            broken.id: RuntimeError("boom"),
        }
    )
    watch = DeteriorationWatch(comparator)
    assert await watch.conditions([stopped, healthy, broken]) == []
    assert comparator.calls == 2  # the stopped bot is never even compared


async def test_watch_skips_a_bot_without_a_comparable_backtest():
    bot = _bot()
    none = RealizedVsBacktest(None, None, None, None, "no completed backtest")
    assert await DeteriorationWatch(FakeComparator({bot.id: none})).conditions([bot]) == []


class _Clock:
    def __init__(self) -> None:
        self.current = T0

    def now(self):  # type: ignore[no-untyped-def]
        return self.current


async def test_monitor_compares_on_its_own_slow_clock_and_reuses_the_last_result():
    bot = _bot()
    calls = 0
    firing = [
        Condition(
            AlertKind.PERFORMANCE_DEGRADED, "performance_degraded:x", AlertSeverity.WARNING, "m"
        )
    ]

    async def deteriorated(bots):  # type: ignore[no-untyped-def]
        nonlocal calls
        calls += 1
        return list(firing)

    clock = _Clock()
    monitor = AlertMonitor(
        None,  # type: ignore[arg-type]
        None,  # type: ignore[arg-type]
        None,  # type: ignore[arg-type]
        clock,
        timedelta(seconds=15),
        timedelta(days=30),
        deterioration=deteriorated,
        deterioration_interval=timedelta(minutes=15),
    )
    assert await monitor._deterioration_firing([bot], clock.current) == firing
    clock.current += timedelta(minutes=5)
    assert await monitor._deterioration_firing([bot], clock.current) == firing  # reused
    assert calls == 1
    clock.current += timedelta(minutes=11)
    firing.clear()  # the condition went away: the next comparison reports nothing
    assert await monitor._deterioration_firing([bot], clock.current) == []
    assert calls == 2


async def test_monitor_without_the_watch_reports_nothing():
    monitor = AlertMonitor(
        None,
        None,
        None,
        _Clock(),
        timedelta(seconds=15),
        timedelta(days=30),  # type: ignore[arg-type]
    )
    assert await monitor._deterioration_firing([_bot()], T0) == []


def test_the_new_alert_kind_is_watched_by_the_worker_and_evaluator_ignores_other_scopes():
    from modules.notifications.application.service import API_SCOPE, WORKER_SCOPE

    assert AlertKind.PERFORMANCE_DEGRADED in WORKER_SCOPE
    assert AlertKind.PERFORMANCE_DEGRADED not in API_SCOPE
