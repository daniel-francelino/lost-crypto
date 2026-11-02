from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any
from uuid import UUID

from modules.market_data.domain.models import Timeframe

# Candles fetched on a fresh start only to warm the strategy up (never traded on).
WARMUP_CANDLES = 300
# Orders are only placed for candles processed shortly after they closed.
MAX_SIGNAL_AGE_CAP = timedelta(minutes=15)
# Consecutive failures after which a bot is put in the error state.
MAX_CONSECUTIVE_FAILURES = 5


class SessionStatus(StrEnum):
    ACTIVE = "active"
    ENDED = "ended"


@dataclass(slots=True)
class TradingSession:
    """One continuous run of a bot. Pausing keeps it; stopping ends it."""

    id: UUID
    bot_id: UUID
    config_version: int
    status: SessionStatus
    started_at: datetime
    strategy_state: dict[str, Any] | None = None
    execution_snapshot: dict[str, Any] | None = None
    last_processed_bar_time: datetime | None = None
    mode: str = "paper"  # the execution mode this run traded in (paper history gate)
    ended_at: datetime | None = None
    end_reason: str | None = None


def max_signal_age(timeframe: Timeframe) -> timedelta:
    """How long after a candle closes a signal on it may still become an order."""
    return min(timeframe.delta / 2, MAX_SIGNAL_AGE_CAP)
