from collections import Counter
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal

from modules.audit.models import AuditEvent

AFTER_DRAWDOWN_PCT = Decimal("5")
INTERVENTION_EVENTS = (
    "bot.pause_requested",
    "bot.stop_requested",
    "bot.portfolio_reset",
    "bot.config_updated",
)
SYSTEM_INTERVENTION_EVENTS = ("system.kill_switch_activated", "system.kill_switch_released")


def summarize(
    events: Sequence[AuditEvent],
    contexts: dict[datetime, tuple[Decimal, Decimal] | None],
    drawdown_threshold: Decimal = AFTER_DRAWDOWN_PCT,
) -> dict[str, object]:
    by_type = Counter(event.event_type for event in events)
    items = []
    after_drawdown = 0
    for event in events:
        context = contexts.get(event.occurred_at) if event.occurred_at is not None else None
        drawdown = None
        if context is not None and context[1] > 0:
            drawdown = (context[1] - context[0]) / context[1] * 100
            if drawdown >= drawdown_threshold:
                after_drawdown += 1
        payload = event.payload or {}
        items.append(
            {
                "at": event.occurred_at,
                "type": event.event_type,
                "actor": event.actor,
                "reason": payload.get("reason"),
                "drawdown_pct": None if drawdown is None else str(drawdown),
            }
        )
    return {
        "total": sum(by_type.values()),
        "after_drawdown": after_drawdown,
        "by_type": dict(by_type),
        "items": items,
    }
