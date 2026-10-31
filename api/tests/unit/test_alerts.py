from collections.abc import AsyncIterator, Collection, Mapping
from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from modules.audit.models import AuditEvent
from modules.bots.domain.models import Bot, BotConfig, BotState, ExecutionMode
from modules.market_data.application.updater import (
    RateLimitPause,
    Series,
    StaleSeries,
    UpdateReport,
)
from modules.market_data.domain.models import Timeframe
from modules.notifications.application import conditions
from modules.notifications.application.evaluator import AlertEvaluator
from modules.notifications.domain.models import (
    Alert,
    AlertKind,
    AlertSeverity,
    Condition,
)
from modules.risk_management.domain.models import KillSwitchState
from modules.trading.application.status import (
    StaleBot,
    SystemStatus,
    WorkerStatus,
)

NOW = datetime(2024, 1, 1, 12, tzinfo=UTC)
COOLDOWN = timedelta(minutes=5)


class FakeClock:
    def __init__(self) -> None:
        self.current = NOW

    def now(self) -> datetime:
        return self.current


class FakeAlerts:
    def __init__(self) -> None:
        self.rows: list[Alert] = []

    async def add(
        self,
        kind: AlertKind,
        severity: AlertSeverity,
        dedupe_key: str,
        message: str,
        bot_id: Any,
        payload: Mapping[str, Any],
        opened_at: datetime,
    ) -> Alert:
        alert = Alert(
            len(self.rows) + 1, kind, severity, dedupe_key, message, bot_id, payload, opened_at
        )
        assert not any(a.dedupe_key == dedupe_key and a.is_open for a in self.rows)
        self.rows.append(alert)
        return replace(alert)

    def _get(self, alert_id: int) -> Alert:
        return next(a for a in self.rows if a.id == alert_id)

    async def list_open(self, kinds: Collection[AlertKind]) -> list[Alert]:
        return [replace(a) for a in self.rows if a.is_open and a.kind in kinds]

    async def latest_for_key(self, dedupe_key: str) -> Alert | None:
        found = [a for a in self.rows if a.dedupe_key == dedupe_key]
        return replace(found[-1]) if found else None

    async def update_open(
        self, alert_id: int, severity: AlertSeverity, message: str, payload: Mapping[str, Any]
    ) -> None:
        alert = self._get(alert_id)
        alert.severity, alert.message, alert.payload = severity, message, payload

    async def reopen(
        self, alert_id: int, severity: AlertSeverity, message: str, payload: Mapping[str, Any]
    ) -> None:
        alert = self._get(alert_id)
        alert.severity, alert.message, alert.payload = severity, message, payload
        alert.resolved_at = alert.read_at = None

    async def resolve(self, alert_id: int, at: datetime) -> None:
        self._get(alert_id).resolved_at = at


class FakeAudit:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    async def add(self, event: AuditEvent) -> None:
        self.events.append(event)


class Harness:
    def __init__(self) -> None:
        self.clock = FakeClock()
        self.alerts = FakeAlerts()
        self.audit = FakeAudit()
        self.commits = 0
        self.evaluator = AlertEvaluator(self._stores, self.clock, COOLDOWN)

    @asynccontextmanager
    async def _stores(self) -> AsyncIterator["Harness"]:
        yield self

    async def commit(self) -> None:
        self.commits += 1

    async def sync(self, *firing: Condition, scope: Collection[AlertKind] | None = None) -> Any:
        return await self.evaluator.sync(scope or set(AlertKind), list(firing), actor="test")


def condition(
    key: str = "k",
    severity: AlertSeverity = AlertSeverity.WARNING,
    message: str = "m",
    kind: AlertKind = AlertKind.BOT_STALE,
) -> Condition:
    return Condition(kind, key, severity, message)


async def test_a_firing_condition_opens_one_alert_and_keeps_it_while_it_fires() -> None:
    h = Harness()
    assert (await h.sync(condition())).opened == 1
    assert (await h.sync(condition())).opened == 0
    assert len(h.alerts.rows) == 1 and h.alerts.rows[0].is_open


async def test_a_changed_message_updates_the_open_alert_without_a_new_one() -> None:
    h = Harness()
    await h.sync(condition(message="a"))
    await h.sync(condition(message="b", severity=AlertSeverity.CRITICAL))
    (alert,) = h.alerts.rows
    assert (alert.message, alert.severity) == ("b", AlertSeverity.CRITICAL)


async def test_a_condition_that_stops_firing_resolves_its_alert() -> None:
    h = Harness()
    await h.sync(condition())
    h.clock.current += timedelta(minutes=1)
    result = await h.sync()
    assert result.resolved == 1
    assert h.alerts.rows[0].resolved_at == h.clock.current


async def test_coming_back_within_the_cooldown_reopens_the_same_alert_as_unread() -> None:
    h = Harness()
    await h.sync(condition())
    await h.sync()
    h.alerts.rows[0].read_at = h.clock.current
    h.clock.current += COOLDOWN - timedelta(seconds=1)
    await h.sync(condition(message="again"))
    (alert,) = h.alerts.rows
    assert alert.is_open and alert.read_at is None and alert.message == "again"


async def test_coming_back_after_the_cooldown_is_a_new_episode() -> None:
    h = Harness()
    await h.sync(condition())
    await h.sync()
    h.clock.current += COOLDOWN
    await h.sync(condition())
    assert len(h.alerts.rows) == 2 and h.alerts.rows[1].is_open


async def test_each_evaluator_only_touches_the_kinds_in_its_scope() -> None:
    h = Harness()
    await h.sync(condition("a", kind=AlertKind.WORKER_DOWN))
    await h.sync(scope={AlertKind.BOT_STALE})
    assert h.alerts.rows[0].is_open
    await h.sync(scope={AlertKind.WORKER_DOWN})
    assert not h.alerts.rows[0].is_open


async def test_only_critical_episodes_reach_the_audit_trail() -> None:
    h = Harness()
    await h.sync(condition("w"), condition("c", AlertSeverity.CRITICAL))
    await h.sync()
    assert [e.event_type for e in h.audit.events] == ["alert.opened", "alert.resolved"]
    assert h.audit.events[0].payload["severity"] == "critical"


def status(
    alive: bool = True,
    last_heartbeat: datetime | None = NOW,
    kill_active: bool = False,
    stale: tuple[StaleBot, ...] = (),
) -> SystemStatus:
    return SystemStatus(
        worker=WorkerStatus(alive, last_heartbeat, 1.0),
        kill_switch=KillSwitchState(active=kill_active, reason="stop" if kill_active else None),
        bots_by_state={},
        stale_bots=list(stale),
        exchanges=["binance"],
    )


def make_bot(
    state: BotState = BotState.RUNNING,
    mode: ExecutionMode = ExecutionMode.PAPER,
    error: str | None = None,
) -> Bot:
    config = BotConfig(
        name="b1",
        strategy_type="ema_crossover",
        strategy_params={},
        symbol="TST/USDT",
        timeframe=Timeframe.H1,
        initial_capital=1000,  # type: ignore[arg-type]
        fee_rate=0,  # type: ignore[arg-type]
        slippage_bps=0,  # type: ignore[arg-type]
        mode=mode,
        connection_id=uuid4() if mode.uses_exchange else None,
    )
    return Bot(
        id=uuid4(),
        config=config,
        desired_state=BotState.RUNNING,
        observed_state=state,
        config_version=1,
        created_at=NOW,
        updated_at=NOW,
        last_error=error,
    )


def test_worker_down_is_critical_and_only_fires_when_the_worker_is_not_alive() -> None:
    assert conditions.worker_down(status()) == []
    (down,) = conditions.worker_down(status(alive=False))
    assert down.kind is AlertKind.WORKER_DOWN and down.severity is AlertSeverity.CRITICAL
    (never,) = conditions.worker_down(status(alive=False, last_heartbeat=None))
    assert "never" in never.message


def test_kill_switch_condition_carries_the_reason() -> None:
    assert conditions.kill_switch(status()) == []
    (active,) = conditions.kill_switch(status(kill_active=True))
    assert active.dedupe_key == "kill_switch" and "stop" in active.message


def test_stale_and_errored_bots_are_warnings_but_critical_when_live() -> None:
    paper, live = make_bot(), make_bot(mode=ExecutionMode.LIVE)
    errored = make_bot(BotState.ERROR, error="boom")
    stale = tuple(StaleBot(str(b.id), b.config.name, NOW, 120.0) for b in (paper, live))
    found = conditions.bots(status(stale=stale), [paper, live, errored])
    by_key = {c.dedupe_key: c for c in found}
    assert by_key[f"bot_stale:{paper.id}"].severity is AlertSeverity.WARNING
    assert by_key[f"bot_stale:{live.id}"].severity is AlertSeverity.CRITICAL
    assert "boom" in by_key[f"bot_error:{errored.id}"].message
    assert len(found) == 3


def test_candle_conditions_cover_stale_series_and_exchange_pauses() -> None:
    series = Series("binance", "BTC/USDT", Timeframe.M1)
    report = UpdateReport(
        stale=(StaleSeries(series, NOW, 5),), rate_limited=(RateLimitPause("binance", NOW),)
    )
    kinds = {c.kind for c in conditions.candles(report)}
    assert kinds == {AlertKind.CANDLES_STALE, AlertKind.EXCHANGE_RATE_LIMITED}
    assert conditions.candles(UpdateReport()) == []
