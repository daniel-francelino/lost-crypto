from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID


class AlertKind(StrEnum):
    WORKER_DOWN = "worker_down"
    BOT_STALE = "bot_stale"
    BOT_ERROR = "bot_error"
    KILL_SWITCH_ACTIVE = "kill_switch_active"
    CANDLES_STALE = "candles_stale"
    EXCHANGE_RATE_LIMITED = "exchange_rate_limited"
    PERFORMANCE_DEGRADED = "performance_degraded"
    PROTECTIVE_EXIT_SLIPPAGE = "protective_exit_slippage"


class AlertSeverity(StrEnum):
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class Condition:
    """Something that is wrong right now. ``dedupe_key`` identifies the episode: while the
    condition keeps firing there is one open alert for the key, never a new one per check."""

    kind: AlertKind
    dedupe_key: str
    severity: AlertSeverity
    message: str
    bot_id: UUID | None = None
    payload: Mapping[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Alert:
    id: int
    kind: AlertKind
    severity: AlertSeverity
    dedupe_key: str
    message: str
    bot_id: UUID | None
    payload: Mapping[str, Any]
    opened_at: datetime
    resolved_at: datetime | None = None
    read_at: datetime | None = None

    @property
    def is_open(self) -> bool:
        return self.resolved_at is None


@dataclass(frozen=True, slots=True)
class AlertSummary:
    unread: int
    open: int
    critical_open: int
