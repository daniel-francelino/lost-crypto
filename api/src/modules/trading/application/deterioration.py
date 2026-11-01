"""Turns the realized-vs-backtest comparison of every running bot into alert conditions."""

import logging
from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from modules.bots.domain.models import Bot, BotState
from modules.notifications.domain.models import AlertKind, AlertSeverity, Condition
from modules.trading.application.comparison import RealizedVsBacktest
from modules.trading.domain.deterioration import Deterioration, deterioration

logger = logging.getLogger(__name__)


class Comparator(Protocol):
    async def compare(self, bot_id: UUID, run_id: UUID | None = None) -> RealizedVsBacktest: ...


def _message(found: Deterioration) -> str:
    parts = []
    if found.sharpe_below_half:
        parts.append("Sharpe real abaixo de metade do backtest")
    if found.drawdown_above_backtest:
        parts.append("drawdown atual acima do máximo do backtest")
    return "Desempenho fora da faixa do backtest: " + " e ".join(parts) + "."


class DeteriorationWatch:
    """Read-only. A failure on one bot is logged and skips that bot only."""

    def __init__(self, comparison: Comparator) -> None:
        self._comparison = comparison

    async def conditions(self, bots: Sequence[Bot]) -> list[Condition]:
        out: list[Condition] = []
        for bot in bots:
            if bot.desired_state is not BotState.RUNNING:
                continue
            try:
                result = await self._comparison.compare(bot.id)
            except Exception:
                logger.exception("deterioration check failed for bot %s", bot.id)
                continue
            if result.comparison is None:
                continue
            found = deterioration(
                result.comparison,
                result.realized_drawdown_pct,
                result.backtest_max_drawdown_pct,
            )
            if found is None:
                continue
            out.append(
                Condition(
                    AlertKind.PERFORMANCE_DEGRADED,
                    f"performance_degraded:{bot.id}",
                    AlertSeverity.WARNING,
                    _message(found),
                    bot_id=bot.id,
                    payload={
                        "sharpe_below_half": found.sharpe_below_half,
                        "drawdown_above_backtest": found.drawdown_above_backtest,
                        "run_id": None if result.run_id is None else str(result.run_id),
                    },
                )
            )
        return out
