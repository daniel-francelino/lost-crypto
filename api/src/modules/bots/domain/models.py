from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID

from core.errors import ConflictError, DomainError
from modules.market_data.domain.models import Timeframe
from modules.risk_management.domain.models import RiskLimits


class ExecutionMode(StrEnum):
    PAPER = "paper"
    # TESTNET = "testnet" and LIVE = "live" arrive in later phases, behind their safeguards.


class BotState(StrEnum):
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"  # observed only: the worker could not keep the bot running


class InvalidBotConfig(DomainError):
    pass


class InvalidBotTransition(ConflictError):
    pass


@dataclass(frozen=True, slots=True)
class BotConfig:
    name: str
    strategy_type: str
    strategy_params: Mapping[str, Any]
    symbol: str
    timeframe: Timeframe
    initial_capital: Decimal
    fee_rate: Decimal
    slippage_bps: Decimal
    risk: RiskLimits = field(default_factory=RiskLimits)
    mode: ExecutionMode = ExecutionMode.PAPER

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise InvalidBotConfig("name must not be empty")
        if self.initial_capital <= 0:
            raise InvalidBotConfig("initial_capital must be positive")
        if not (0 <= self.fee_rate < 1):
            raise InvalidBotConfig("fee_rate must be in [0, 1)")
        if not (0 <= self.slippage_bps < 10_000):
            raise InvalidBotConfig("slippage_bps must be in [0, 10000)")


@dataclass(slots=True)
class Bot:
    """The API changes ``desired_state``; only the worker changes ``observed_state``."""

    id: UUID
    config: BotConfig
    desired_state: BotState
    observed_state: BotState
    config_version: int
    created_at: datetime
    updated_at: datetime
    last_heartbeat_at: datetime | None = None
    last_error: str | None = None

    def request_start(self) -> None:
        if self.desired_state is BotState.RUNNING:
            raise InvalidBotTransition("bot is already running")
        self.desired_state = BotState.RUNNING

    def request_pause(self) -> None:
        if self.desired_state is not BotState.RUNNING:
            raise InvalidBotTransition("only a running bot can be paused")
        self.desired_state = BotState.PAUSED

    def request_stop(self) -> None:
        if self.desired_state is BotState.STOPPED and self.observed_state is BotState.STOPPED:
            raise InvalidBotTransition("bot is already stopped")
        self.desired_state = BotState.STOPPED

    def ensure_editable(self) -> None:
        if self.desired_state is not BotState.STOPPED or self.observed_state not in (
            BotState.STOPPED,
            BotState.ERROR,
        ):
            raise InvalidBotTransition("stop the bot before changing its configuration")
