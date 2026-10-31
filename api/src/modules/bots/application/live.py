"""Gate to REAL MONEY: readiness checklist, typed confirmation, one-time approval token.

Nothing here sends an order. It decides whether a human may switch a bot to live, and records the
explicit approval the worker later insists on. Principles (doc 05):

* every check must pass, none is advisory;
* the approval is a short-lived, single-use token bound to ONE configuration version, so any
  later change to the bot invalidates it;
* the worker re-checks the approval and every safeguard on each pass, so bypassing the API (for
  example editing the database) still cannot make a live bot trade.
"""

import hashlib
import secrets
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from core.clock import Clock
from core.config import AppEnv, Settings
from core.errors import ConflictError, DomainError
from core.ids import IdGenerator
from modules.audit.models import AuditEvent
from modules.bots.application.errors import BotNotFound
from modules.bots.application.ports import BotStore, LiveApproval
from modules.bots.domain.models import Bot, BotState, ExecutionMode
from modules.exchanges.domain.connections import ConnectionStatus, Environment

#: Events that disqualify a bot's history: it must have run cleanly before touching real money.
DISQUALIFYING_EVENTS = (
    "risk.daily_loss_breached",
    "risk.drawdown_breached",
    "risk.consecutive_losses",
    "risk.live_daily_loss_cap",
    "reconciliation.mismatch",
    "bot.error",
)

BotStoreFactory = Callable[[], AbstractAsyncContextManager[BotStore]]


class LiveNotApproved(DomainError):
    """The confirmation token is missing, wrong, expired, used or for another version."""


class NotReadyForLive(ConflictError):
    pass


@dataclass(frozen=True, slots=True)
class Check:
    name: str
    ok: bool
    detail: str


@dataclass(frozen=True, slots=True)
class Readiness:
    checks: list[Check]

    @property
    def ready(self) -> bool:
        return all(c.ok for c in self.checks)


@dataclass(frozen=True, slots=True)
class IssuedApproval:
    token: str
    expires_at: datetime


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class LiveService:
    def __init__(
        self, stores: BotStoreFactory, settings: Settings, clock: Clock, ids: IdGenerator
    ) -> None:
        self._stores = stores
        self._settings = settings
        self._clock = clock
        self._ids = ids

    async def readiness(self, store: BotStore, bot: Bot) -> Readiness:
        s, cfg = self._settings, bot.config
        checks = [
            Check(
                "mode",
                cfg.mode is ExecutionMode.LIVE,
                f"bot mode is {cfg.mode.value}; promote it to live first",
            ),
            Check(
                "stopped",
                bot.desired_state is BotState.STOPPED and bot.observed_state is BotState.STOPPED,
                "stop the bot before approving it for live trading",
            ),
            Check(
                "environment",
                s.app_env is AppEnv.PROD,
                f"APP_ENV is {s.app_env.value}; live trading only runs with APP_ENV=prod",
            ),
            Check(
                "hard caps",
                s.live_caps_configured,
                "set LIVE_MAX_ORDER_NOTIONAL, LIVE_MAX_TOTAL_EXPOSURE and LIVE_MAX_DAILY_LOSS",
            ),
        ]

        connection = await store.connections.get(cfg.connection_id) if cfg.connection_id else None
        checks.append(
            Check(
                "live connection",
                connection is not None
                and connection.environment is Environment.LIVE
                and connection.status is ConnectionStatus.ACTIVE
                and connection.exchange == cfg.exchange,
                "needs an ACTIVE live connection for this exchange (keys verified trade-only)"
                if connection is None or connection.status is not ConnectionStatus.ACTIVE
                else "connection must be a live connection of this bot's exchange",
            )
        )
        checks.append(
            Check(
                "risk limits",
                cfg.risk.require_stop_loss and cfg.risk.max_daily_loss_pct is not None,
                "live bots must set risk.require_stop_loss=true and risk.max_daily_loss_pct",
            )
        )
        cap = s.live_max_total_exposure
        checks.append(
            Check(
                "capital within caps",
                cap is not None and cfg.initial_capital <= cap,
                f"initial_capital {cfg.initial_capital} exceeds LIVE_MAX_TOTAL_EXPOSURE {cap}",
            )
        )

        first, last = await store.portfolio.paper_span(bot.id)
        days = 0.0 if first is None or last is None else (last - first).total_seconds() / 86400
        checks.append(
            Check(
                "paper history",
                days >= s.live_min_paper_days,
                f"{days:.1f} days of paper trading; {s.live_min_paper_days} required",
            )
        )
        # Only the history that EARNED the promotion counts. What happens after a bot is
        # promoted (a pause, a misconfigured worker) is handled by the live caps and the kill
        # switch, and must not permanently disqualify it.
        promoted_at = await store.audit.latest_event_time(bot.id, "live.promoted")
        breaches = await store.audit.count_events(bot.id, DISQUALIFYING_EVENTS, before=promoted_at)
        checks.append(
            Check(
                "clean history",
                breaches == 0,
                f"{breaches} risk breach/error event(s) before promotion; start a new bot",
            )
        )
        return Readiness(checks)

    async def evaluate(self, bot_id: Any) -> tuple[Bot, Readiness]:
        async with self._stores() as store:
            bot = await store.bots.get(bot_id)
            if bot is None:
                raise BotNotFound(str(bot_id))
            return bot, await self.readiness(store, bot)

    async def request_approval(self, bot_id: Any, typed_name: str, actor: str) -> IssuedApproval:
        """Step one of two: prove readiness and that a human typed the bot's exact name."""
        now = self._clock.now()
        async with self._stores() as store:
            bot = await store.bots.get(bot_id)
            if bot is None:
                raise BotNotFound(str(bot_id))
            readiness = await self.readiness(store, bot)
            if not readiness.ready:
                failed = "; ".join(f"{c.name}: {c.detail}" for c in readiness.checks if not c.ok)
                raise NotReadyForLive(f"not ready for live trading: {failed}")
            if typed_name != bot.config.name:
                raise LiveNotApproved("type the bot's exact name to confirm")

            await store.live_approvals.supersede(bot.id, now)  # only the latest request counts
            token = secrets.token_urlsafe(32)
            expires_at = now + timedelta(minutes=self._settings.live_approval_minutes)
            await store.live_approvals.add(
                LiveApproval(
                    self._ids.new_id(),
                    bot.id,
                    bot.config_version,
                    _hash(token),
                    actor,
                    now,
                    expires_at,
                )
            )
            await store.audit.add(
                AuditEvent(
                    "live.approval_requested",
                    "bot",
                    str(bot.id),
                    actor=actor,
                    bot_id=bot.id,
                    payload={"config_version": bot.config_version},
                )
            )
            await store.commit()
        return IssuedApproval(token, expires_at)

    async def consume(self, store: BotStore, bot: Bot, token: str | None, actor: str) -> None:
        """Step two, inside the start command: spend the token and record the approval.

        EVERY start of a live bot spends a fresh token, including a resume after a pause or a
        kill switch: real money never restarts on an old decision."""
        now = self._clock.now()
        if not token:
            raise LiveNotApproved("a live bot needs a confirmation_token to start")
        approval = await store.live_approvals.find(bot.id, _hash(token))
        if (
            approval is None
            or approval.used_at is not None
            or approval.expires_at <= now
            or approval.config_version != bot.config_version
        ):
            raise LiveNotApproved("confirmation token is invalid, expired, used or outdated")
        readiness = await self.readiness(store, bot)
        # 'stopped' is satisfied by definition while the start command is being processed.
        blocking = [c for c in readiness.checks if not c.ok and c.name != "stopped"]
        if blocking:
            raise NotReadyForLive(
                "not ready for live trading: "
                + "; ".join(f"{c.name}: {c.detail}" for c in blocking)
            )
        await store.live_approvals.mark_used(approval.id, now)
        await store.bots.set_live_approval(bot.id, bot.config_version, now)
        bot.live_approved_config_version, bot.live_approved_at = bot.config_version, now
        await store.audit.add(
            AuditEvent(
                "live.activated",
                "bot",
                str(bot.id),
                actor=actor,
                bot_id=bot.id,
                payload={"config_version": bot.config_version},
            )
        )
