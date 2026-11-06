import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from core.errors import DomainError
from modules.bots.domain.models import BotState, ExecutionMode
from modules.exchanges.application.ports import ExchangePosition, FundingIncome
from modules.exchanges.domain.models import MarginMode, PositionSide, TradingProduct
from modules.portfolio.domain.perpetual_ledger import (
    PerpetualLedgerEntry,
    PerpetualLedgerEventKind,
)
from modules.portfolio.domain.perpetuals import PerpetualLedger
from modules.trading.application.futures_user_stream import FuturesUserStreamMonitor


class _Exchange:
    capabilities = SimpleNamespace(exchange_id="binance-usdm")

    def __init__(self) -> None:
        self.calls = 0
        self.reconnected = asyncio.Event()

    async def stream_user_events(self):
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("simulated socket gap")
        self.reconnected.set()
        await asyncio.Event().wait()
        if False:
            yield {}


class _Resolver:
    def __init__(self, exchange: _Exchange) -> None:
        self.exchange = exchange

    async def exchange_for(self, connection_id):
        return self.exchange


class _Reconciler:
    def __init__(self) -> None:
        self.reconciliations = 0

    async def resolve_pending(self, connection_id) -> None:
        return None

    async def reconcile_connection(self, connection_id, **_kwargs) -> None:
        self.reconciliations += 1
        if self.reconciliations == 2:
            raise RuntimeError("simulated REST outage")


class _Bots:
    async def list_bots(self, limit: int):
        return []


class _Executor:
    def __init__(self) -> None:
        self.synced: list[object] = []

    async def sync_native_stop(self, bot) -> None:
        self.synced.append(bot)


class _EventExchange:
    capabilities = SimpleNamespace(exchange_id="binance-usdm")

    def __init__(self) -> None:
        self.calls = 0
        self.reconnected = asyncio.Event()

    async def stream_user_events(self):
        self.calls += 1
        if self.calls == 1:
            yield {"e": "ORDER_TRADE_UPDATE"}
            return
        self.reconnected.set()
        await asyncio.Event().wait()
        if False:
            yield {}


@asynccontextmanager
async def _stores():
    yield SimpleNamespace(bots=_Bots())


@pytest.mark.asyncio
async def test_stream_reconnect_waits_for_pause_and_successful_rest_reconciliation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def no_wait(_seconds: float) -> None:
        return None

    monkeypatch.setattr(asyncio, "sleep", no_wait)
    exchange = _Exchange()
    reconciler = _Reconciler()
    pauses: list[tuple[str, str]] = []
    monitor = FuturesUserStreamMonitor(
        stores=_stores,
        resolver=_Resolver(exchange),  # type: ignore[arg-type]
        reconciler=reconciler,  # type: ignore[arg-type]
        executor=_Executor(),  # type: ignore[arg-type]
        clock=None,  # type: ignore[arg-type]
    )

    async def record_pause(connection_id, event_type: str, reason: str) -> None:
        pauses.append((event_type, reason))

    monkeypatch.setattr(monitor, "_pause_connection", record_pause)
    task = asyncio.create_task(monitor._run_connection(uuid4()))
    try:
        await asyncio.wait_for(exchange.reconnected.wait(), timeout=1)
        assert exchange.calls == 2
        # Initial snapshot, successful post-gap recovery snapshot, and pre-reconnect snapshot.
        assert reconciler.reconciliations == 4
        assert len(pauses) == 2
        assert all(event == "risk.futures_user_stream_disconnected" for event, _ in pauses)
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task


@pytest.mark.asyncio
async def test_protective_stop_sync_is_scoped_to_exchange_futures_bots() -> None:
    connection_id = uuid4()
    futures_bot = SimpleNamespace(
        desired_state=BotState.RUNNING,
        observed_state=BotState.RUNNING,
        config=SimpleNamespace(
            connection_id=connection_id,
            product=TradingProduct.LINEAR_PERPETUAL,
            mode=ExecutionMode.TESTNET,
        ),
    )
    spot_bot = SimpleNamespace(
        config=SimpleNamespace(
            connection_id=connection_id,
            product=TradingProduct.SPOT,
            mode=ExecutionMode.TESTNET,
        )
    )
    paper_bot = SimpleNamespace(
        config=SimpleNamespace(
            connection_id=connection_id,
            product=TradingProduct.LINEAR_PERPETUAL,
            mode=ExecutionMode.PAPER,
        )
    )

    class Bots:
        async def list_bots(self, limit: int):
            return [futures_bot, spot_bot, paper_bot]

    @asynccontextmanager
    async def stores():
        yield SimpleNamespace(bots=Bots())

    executor = _Executor()
    monitor = FuturesUserStreamMonitor(
        stores,  # type: ignore[arg-type]
        None,  # type: ignore[arg-type]
        None,  # type: ignore[arg-type]
        executor,  # type: ignore[arg-type]
        None,  # type: ignore[arg-type]
    )

    await monitor._sync_protective_stops(connection_id)

    assert executor.synced == [futures_bot]


@pytest.mark.asyncio
async def test_order_event_syncs_protective_stops_before_account_reconciliation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def no_wait(_seconds: float) -> None:
        return None

    monkeypatch.setattr(asyncio, "sleep", no_wait)
    exchange = _EventExchange()
    timeline: list[str] = []

    class Resolver(_Resolver):
        async def exchange_for(self, connection_id):
            return exchange

    class Reconciler:
        async def resolve_pending(self, connection_id) -> None:
            timeline.append("resolve")

        async def reconcile_connection(self, connection_id, **_kwargs) -> None:
            timeline.append("reconcile")

    monitor = FuturesUserStreamMonitor(
        _stores,  # type: ignore[arg-type]
        Resolver(exchange),  # type: ignore[arg-type]
        Reconciler(),  # type: ignore[arg-type]
        _Executor(),  # type: ignore[arg-type]
        None,  # type: ignore[arg-type]
    )

    async def sync_stops(connection_id) -> None:
        timeline.append("sync_stops")

    async def pause(connection_id, event_type: str, reason: str) -> None:
        timeline.append("pause")

    monkeypatch.setattr(monitor, "_sync_protective_stops", sync_stops)
    monkeypatch.setattr(monitor, "_pause_connection", pause)
    task = asyncio.create_task(monitor._run_connection(uuid4()))
    try:
        await asyncio.wait_for(exchange.reconnected.wait(), timeout=1)
        assert timeline[:5] == [
            "resolve",
            "sync_stops",
            "reconcile",
            "resolve",
            "sync_stops",
        ]
        event_resolve = timeline.index("resolve", 3)
        event_sync = timeline.index("sync_stops", event_resolve)
        event_reconcile = timeline.index("reconcile", event_sync)
        pause = timeline.index("pause", event_sync)
        recovery_resolve = timeline.index("resolve", pause)
        recovery_sync = timeline.index("sync_stops", recovery_resolve)
        recovery_reconcile = timeline.index("reconcile", recovery_sync)
        assert event_sync < event_reconcile < pause < recovery_resolve
        assert recovery_resolve < recovery_sync < recovery_reconcile
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task


@pytest.mark.asyncio
async def test_funding_account_update_uses_real_income_and_is_idempotent() -> None:
    connection_id = uuid4()
    bot_id = uuid4()
    bot = SimpleNamespace(
        id=bot_id,
        desired_state=BotState.RUNNING,
        observed_state=BotState.RUNNING,
        config=SimpleNamespace(
            connection_id=connection_id,
            product=TradingProduct.LINEAR_PERPETUAL,
            mode=ExecutionMode.TESTNET,
            symbol="BTC/USDT:USDT",
        ),
    )
    ledger = PerpetualLedger.new(bot_id, Decimal("1000"))
    ledger.open_position(PositionSide.LONG, Decimal("1"), Decimal("100"), leverage=2)

    class LedgerRepository:
        def __init__(self) -> None:
            self.ledger = ledger
            self.entries = []

        async def get(self, requested_bot_id):
            return self.ledger if requested_bot_id == bot_id else None

        async def has_entry(self, requested_bot_id, reference):
            return any(
                entry.bot_id == requested_bot_id and entry.external_reference == reference
                for entry in self.entries
            )

        async def append_entry(self, entry):
            self.entries.append(entry)
            return True

        async def save(self, updated_ledger):
            self.ledger = updated_ledger

    ledger_repository = LedgerRepository()
    audit_events = []

    class Bots:
        async def list_bots(self, limit: int):
            return [bot]

    class Audit:
        async def add(self, event):
            audit_events.append(event)

    @asynccontextmanager
    async def stores():
        store = SimpleNamespace(
            bots=Bots(),
            perpetual_portfolio=ledger_repository,
            audit=Audit(),
            commits=0,
        )

        async def commit() -> None:
            store.commits += 1

        store.commit = commit
        yield store

    class Exchange:
        async def fetch_funding_income(self, symbol, start, end, limit):
            assert symbol == "BTC/USDT:USDT"
            assert limit == 1000
            income_time = datetime.fromtimestamp(event_time_ms / 1000, UTC)
            return [FundingIncome("tx-1", symbol, "USDT", Decimal("-2"), income_time)]

    event_time_ms = int(datetime(2026, 1, 1, 8, tzinfo=UTC).timestamp() * 1000)
    monitor = FuturesUserStreamMonitor(
        stores,  # type: ignore[arg-type]
        None,  # type: ignore[arg-type]
        None,  # type: ignore[arg-type]
        None,  # type: ignore[arg-type]
        None,  # type: ignore[arg-type]
    )
    event = {
        "T": event_time_ms,
        "a": {
            "m": "FUNDING_FEE",
            "S": "BTCUSDT",
            "P": [{"s": "BTCUSDT", "mt": "isolated", "iw": "48"}],
        },
    }

    await monitor._settle_funding_income(connection_id, Exchange(), event)  # type: ignore[arg-type]
    await monitor._settle_funding_income(connection_id, Exchange(), event)  # type: ignore[arg-type]

    assert ledger_repository.ledger.position is not None
    assert ledger_repository.ledger.position.isolated_margin == Decimal("48")
    assert ledger_repository.ledger.funding_paid == Decimal("2")
    assert len(ledger_repository.entries) == 1
    assert ledger_repository.entries[0].external_reference == "binance:funding:tx-1"
    assert len(audit_events) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("remote_margin", "post_funding_position_change", "expected_error"),
    [
        (Decimal("48"), False, None),
        (Decimal("60"), False, "isolated-margin drift exceeds"),
        (Decimal("48"), True, "unreconciled funding predates"),
    ],
)
async def test_funding_recovery_backfills_only_explainable_income(
    remote_margin: Decimal,
    post_funding_position_change: bool,
    expected_error: str | None,
) -> None:
    connection_id = uuid4()
    bot_id = uuid4()
    now = datetime.now(UTC)
    income_time = now - timedelta(minutes=5)
    position_opened_at = income_time - timedelta(days=1)
    bot = SimpleNamespace(
        id=bot_id,
        desired_state=BotState.RUNNING,
        observed_state=BotState.RUNNING,
        config=SimpleNamespace(
            connection_id=connection_id,
            product=TradingProduct.LINEAR_PERPETUAL,
            mode=ExecutionMode.TESTNET,
            symbol="BTC/USDT:USDT",
        ),
    )
    ledger = PerpetualLedger.new(bot_id, Decimal("1000"))
    ledger.open_position(PositionSide.LONG, Decimal("1"), Decimal("100"), leverage=2)
    open_entry = PerpetualLedgerEntry(
        id=uuid4(),
        bot_id=bot_id,
        occurred_at=position_opened_at,
        kind=PerpetualLedgerEventKind.POSITION_OPENED,
        quantity=Decimal("1"),
        side=PositionSide.LONG,
        price=Decimal("100"),
    )
    position_entries = [open_entry]
    if post_funding_position_change:
        position_entries.append(
            PerpetualLedgerEntry(
                id=uuid4(),
                bot_id=bot_id,
                occurred_at=income_time + timedelta(seconds=1),
                kind=PerpetualLedgerEventKind.POSITION_REDUCED,
                quantity=Decimal("0.1"),
                side=PositionSide.LONG,
                price=Decimal("101"),
            )
        )

    class LedgerRepository:
        def __init__(self) -> None:
            self.ledger = ledger
            self.entries = list(position_entries)

        async def get(self, requested_bot_id):
            return self.ledger if requested_bot_id == bot_id else None

        async def has_entry(self, requested_bot_id, reference):
            return any(
                entry.bot_id == requested_bot_id and entry.external_reference == reference
                for entry in self.entries
            )

        async def list_entries(self, requested_bot_id):
            return [entry for entry in self.entries if entry.bot_id == requested_bot_id]

        async def append_entry(self, entry):
            self.entries.append(entry)
            return True

        async def save(self, updated_ledger):
            self.ledger = updated_ledger

    ledger_repository = LedgerRepository()
    audit_events = []

    class Bots:
        async def list_bots(self, limit: int):
            return [bot]

    class Orders:
        async def count_unresolved(self, requested_bot_id):
            return 0

    class Audit:
        async def add(self, event):
            audit_events.append(event)

    @asynccontextmanager
    async def stores():
        store = SimpleNamespace(
            bots=Bots(),
            orders=Orders(),
            perpetual_portfolio=ledger_repository,
            audit=Audit(),
        )

        async def commit() -> None:
            return None

        store.commit = commit
        yield store

    class Exchange:
        async def fetch_funding_income(self, symbol, start, end, limit):
            return [FundingIncome("tx-recovered", symbol, "USDT", Decimal("-2"), income_time)]

        async def fetch_positions(self, symbols):
            return [
                ExchangePosition(
                    symbol="BTC/USDT:USDT",
                    side=PositionSide.LONG,
                    quantity=Decimal("1"),
                    entry_price=Decimal("100"),
                    mark_price=Decimal("99"),
                    unrealized_pnl=Decimal("-1"),
                    leverage=2,
                    margin_mode=MarginMode.ISOLATED,
                    isolated_margin=remote_margin,
                    liquidation_price=Decimal("52"),
                    notional=Decimal("99"),
                )
            ]

    monitor = FuturesUserStreamMonitor(
        stores,  # type: ignore[arg-type]
        None,  # type: ignore[arg-type]
        None,  # type: ignore[arg-type]
        None,  # type: ignore[arg-type]
        SimpleNamespace(now=lambda: now),  # type: ignore[arg-type]
    )

    if expected_error is not None:
        with pytest.raises(DomainError, match=expected_error):
            await monitor._recover_funding_income(connection_id, Exchange())  # type: ignore[arg-type]
        assert len(ledger_repository.entries) == len(position_entries)
        assert audit_events == []
        return

    await monitor._recover_funding_income(connection_id, Exchange())  # type: ignore[arg-type]
    # A worker restart can replay the same 89-day income window. Binance transaction IDs make
    # that backfill idempotent, so neither the ledger nor the audit trail may duplicate it.
    await monitor._recover_funding_income(connection_id, Exchange())  # type: ignore[arg-type]

    assert ledger_repository.ledger.position is not None
    assert ledger_repository.ledger.position.isolated_margin == Decimal("48")
    assert ledger_repository.ledger.funding_paid == Decimal("2")
    assert len(ledger_repository.entries) == 2
    assert ledger_repository.entries[-1].external_reference == "binance:funding:tx-recovered"
    assert audit_events[0].event_type == "futures.funding_backfilled"


@pytest.mark.asyncio
async def test_funding_income_pagination_advances_and_deduplicates_overlapping_pages() -> None:
    symbol = "BTC/USDT:USDT"
    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = start + timedelta(days=1)
    first_page = [
        FundingIncome(
            f"tx-{index}",
            symbol,
            "USDT",
            Decimal("-0.01"),
            start + timedelta(seconds=index),
        )
        for index in range(1000)
    ]
    final_row = FundingIncome(
        "tx-final", symbol, "USDT", Decimal("0.02"), start + timedelta(seconds=1001)
    )

    class Exchange:
        def __init__(self) -> None:
            self.starts: list[datetime] = []

        async def fetch_funding_income(self, requested_symbol, page_start, page_end, limit):
            assert requested_symbol == symbol
            assert page_end == end
            assert limit == 1000
            self.starts.append(page_start)
            if len(self.starts) == 1:
                return first_page
            # Exchanges can return an overlapping boundary row. Its transaction ID is stable.
            return [first_page[-1], final_row]

    exchange = Exchange()
    rows = await FuturesUserStreamMonitor._funding_income_pages(
        symbol,
        start,
        end,
        exchange,  # type: ignore[arg-type]
    )

    assert len(rows) == 1001
    assert len({row.transaction_id for row in rows}) == 1001
    assert rows[-1] == final_row
    assert exchange.starts == [start, first_page[-1].occurred_at + timedelta(milliseconds=1)]


@pytest.mark.asyncio
async def test_funding_income_pagination_rejects_a_page_that_moves_backwards() -> None:
    symbol = "BTC/USDT:USDT"
    start = datetime(2026, 1, 1, tzinfo=UTC)
    rows = [
        FundingIncome(
            f"tx-{index}",
            symbol,
            "USDT",
            Decimal("-0.01"),
            start + timedelta(seconds=index),
        )
        for index in range(1000)
    ]

    class Exchange:
        async def fetch_funding_income(self, requested_symbol, page_start, end, limit):
            assert requested_symbol == symbol
            assert limit == 1000
            return rows

    with pytest.raises(DomainError, match="pagination moved backwards"):
        await FuturesUserStreamMonitor._funding_income_pages(
            symbol,
            start,
            start + timedelta(days=1),
            Exchange(),  # type: ignore[arg-type]
        )


def _scripted_monitor(streams):
    """A monitor whose exchange serves the scripted streams one after another."""
    from types import SimpleNamespace

    calls: list[str] = []
    pauses: list[str] = []
    reconnected = asyncio.Event()

    class Exchange:
        capabilities = SimpleNamespace(exchange_id="binance-usdm")

        def __init__(self) -> None:
            self.opened = 0

        async def stream_user_events(self):
            script = streams[min(self.opened, len(streams) - 1)]
            self.opened += 1
            if self.opened >= 2:
                reconnected.set()
            for item in script:
                if isinstance(item, Exception):
                    raise item
                yield item
            if self.opened >= 2:
                await asyncio.sleep(3600)  # the second connection simply stays up

    exchange = Exchange()

    class Resolver:
        async def exchange_for(self, _connection_id):
            return exchange

    class Reconciler:
        async def resolve_pending(self, _connection_id):
            calls.append("resolve_pending")

        async def reconcile_connection(self, _connection_id, **_kwargs) -> int:
            calls.append("reconcile")
            return 0

    monitor = FuturesUserStreamMonitor(
        _stores, Resolver(), Reconciler(), _Executor(), None  # type: ignore[arg-type]
    )

    async def noop(*_args, **_kwargs) -> None:
        return None

    async def record_pause(_connection_id, event_type: str, reason: str) -> None:
        pauses.append(event_type)

    monitor._sync_protective_stops = noop  # type: ignore[method-assign]
    monitor._recover_funding_income = noop  # type: ignore[method-assign]
    monitor._pause_connection = record_pause  # type: ignore[method-assign]
    return monitor, calls, pauses, reconnected


@pytest.mark.asyncio
async def test_expired_listen_key_resyncs_and_reconnects_without_pausing_the_bots() -> None:
    monitor, calls, pauses, reconnected = _scripted_monitor([[{"e": "listenKeyExpired"}]])
    task = asyncio.create_task(monitor._run_connection(uuid4()))

    await asyncio.wait_for(reconnected.wait(), timeout=2)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)

    assert pauses == []
    # Resynced over REST before each connection: the startup pass and the scheduled reconnect.
    assert calls.count("reconcile") >= 2


@pytest.mark.asyncio
async def test_unexpected_stream_end_still_pauses_the_bots() -> None:
    from modules.exchanges.errors import ExchangeError

    monitor, _calls, pauses, reconnected = _scripted_monitor(
        [[ExchangeError("Binance USD-M private stream disconnected")], []]
    )
    task = asyncio.create_task(monitor._run_connection(uuid4()))

    await asyncio.wait_for(reconnected.wait(), timeout=5)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)

    assert pauses == ["risk.futures_user_stream_disconnected"]


def test_only_a_stream_that_lived_about_a_day_counts_as_a_scheduled_end() -> None:
    from modules.trading.application.futures_user_stream import PLANNED_STREAM_END_SECONDS

    async def check() -> None:
        now = asyncio.get_running_loop().time()
        assert FuturesUserStreamMonitor._is_planned_end(None, False) is False
        assert FuturesUserStreamMonitor._is_planned_end(now, False) is False
        assert FuturesUserStreamMonitor._is_planned_end(now - PLANNED_STREAM_END_SECONDS, False)
        assert FuturesUserStreamMonitor._is_planned_end(now, True) is True

    asyncio.run(check())
