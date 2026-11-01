"""Parity between what a bot did and what the backtester does on the same candles.

Book 1 ch. 5 (C4, p. 89): compare the paper trades with a backtest run on the same recent data;
differences not explained by costs (or an expected execution delay) mean bugs. The replay uses
the bot's own timing (fill at the signal candle's close) and risk limits, so what remains is
classified:

* ``match``: same signal, same decision, same price.
* ``cost``: same trade, different price (slippage, a real exchange's fill).
* ``risk``: one side's risk module refused what the other accepted.
* ``operational``: the bot refused for a reason a backtest cannot have (signal processed too
  late, an order still unresolved, the kill switch, a key or clock warning, live hard caps).
* ``data``: the replay is missing the candle (it was never stored, or was invalid).
* ``unexplained``: anything else. These are the ones that point to a bug.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import StrEnum

from modules.strategies.domain.types import Side

PRICE_TOLERANCE = Decimal("0.00000001")
APPROVED = "approved"
DISCARDED = "discarded_stale"
PROTECTIVE_PREFIXES = ("stop_loss triggered", "take_profit triggered")
_OPERATIONAL_MARKERS = (
    "unresolved",
    "hard caps",
    "permissions changed",
    "server clock",
    "kill switch",
    "global",
)


class ParityClass(StrEnum):
    MATCH = "match"
    COST = "cost"
    RISK = "risk"
    OPERATIONAL = "operational"
    DATA = "data"
    UNEXPLAINED = "unexplained"


@dataclass(frozen=True, slots=True)
class BotSignal:
    bar_time: datetime
    side: Side
    reason: str
    decision: str
    decision_reason: str | None
    fill_price: Decimal | None  # average fill of the order this signal produced, if any


@dataclass(frozen=True, slots=True)
class ReplayEvent:
    bar_time: datetime
    side: Side
    executed: bool
    price: Decimal | None
    reason: str | None  # why the replay refused it


@dataclass(frozen=True, slots=True)
class Difference:
    bar_time: datetime
    side: Side
    kind: ParityClass
    bot: str
    replay: str


def _is_operational(signal: BotSignal) -> bool:
    if signal.decision == DISCARDED:
        return True
    reason = (signal.decision_reason or "").lower()
    return any(marker in reason for marker in _OPERATIONAL_MARKERS)


def _bot_text(signal: BotSignal) -> str:
    if signal.decision == APPROVED:
        price = "" if signal.fill_price is None else f" at {signal.fill_price}"
        return f"executed{price}"
    return f"{signal.decision}: {signal.decision_reason or '-'}"


def _replay_text(event: ReplayEvent | None) -> str:
    if event is None:
        return "no signal"
    if event.executed:
        return f"executed at {event.price}"
    return f"refused: {event.reason or '-'}"


def _classify(signal: BotSignal, event: ReplayEvent | None, has_candle: bool) -> ParityClass:
    if not has_candle:
        return ParityClass.DATA
    if event is None:
        return ParityClass.UNEXPLAINED
    bot_done = signal.decision == APPROVED
    if bot_done and event.executed:
        if signal.fill_price is None or event.price is None:
            return ParityClass.MATCH
        same = abs(signal.fill_price - event.price) <= PRICE_TOLERANCE
        return ParityClass.MATCH if same else ParityClass.COST
    if not bot_done and _is_operational(signal):
        return ParityClass.OPERATIONAL if event.executed else ParityClass.MATCH
    if bot_done != event.executed:
        return ParityClass.RISK
    return ParityClass.MATCH  # both refused


def compare(
    bot_signals: Sequence[BotSignal],
    replay: Sequence[ReplayEvent],
    candle_times: set[datetime],
) -> list[Difference]:
    """Every bot signal and every replay event, classified (``match`` included)."""
    by_key: dict[tuple[datetime, Side], ReplayEvent] = {}
    for event in replay:
        by_key.setdefault((event.bar_time, event.side), event)
    seen: set[tuple[datetime, Side]] = set()
    out: list[Difference] = []
    for signal in sorted(bot_signals, key=lambda s: (s.bar_time, s.side.value)):
        key = (signal.bar_time, signal.side)
        seen.add(key)
        found = by_key.get(key)
        kind = _classify(signal, found, signal.bar_time in candle_times)
        out.append(
            Difference(signal.bar_time, signal.side, kind, _bot_text(signal), _replay_text(found))
        )
    for event in replay:
        key = (event.bar_time, event.side)
        if key in seen:
            continue
        seen.add(key)
        kind = ParityClass.UNEXPLAINED if event.executed else ParityClass.MATCH
        out.append(Difference(event.bar_time, event.side, kind, "no signal", _replay_text(event)))
    return sorted(out, key=lambda d: (d.bar_time, d.side.value))


def bar_of_fill(fill_time: datetime, candle_closes: set[datetime], step: timedelta) -> datetime:
    """The signal candle of a replay fill: fills at a candle's close belong to that candle,
    protective fills (at a candle's open time) to the candle they happened in."""
    return fill_time - step if fill_time in candle_closes else fill_time
