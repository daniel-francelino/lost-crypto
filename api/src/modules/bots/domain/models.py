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
    PAPER = "paper"  # simulated fills at real prices, no exchange account
    TESTNET = "testnet"  # real orders on the exchange sandbox (fake money), needs a connection
    LIVE = "live"  # REAL MONEY: only behind the safeguards of doc 05 / doc 13

    @property
    def uses_exchange(self) -> bool:
        """Orders go to a real exchange account (sandbox or not) instead of the simulator."""
        return self is not ExecutionMode.PAPER


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
    exchange: str = "binance"
    connection_id: UUID | None = None  # credentials used by testnet bots

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise InvalidBotConfig("name must not be empty")
        if self.initial_capital <= 0:
            raise InvalidBotConfig("initial_capital must be positive")
        if not (0 <= self.fee_rate < 1):
            raise InvalidBotConfig("fee_rate must be in [0, 1)")
        if not (0 <= self.slippage_bps < 10_000):
            raise InvalidBotConfig("slippage_bps must be in [0, 10000)")
        if self.mode.uses_exchange and self.connection_id is None:
            raise InvalidBotConfig(
                f"a {self.mode.value} bot needs an exchange connection (connection_id)"
            )
        if self.mode is ExecutionMode.PAPER and self.connection_id is not None:
            raise InvalidBotConfig("paper bots do not use an exchange connection")


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
    # Live only: the config version a human explicitly approved. Any configuration change bumps
    # config_version, which silently invalidates the approval.
    live_approved_config_version: int | None = None
    live_approved_at: datetime | None = None

    @property
    def has_live_approval(self) -> bool:
        return self.live_approved_config_version == self.config_version

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
