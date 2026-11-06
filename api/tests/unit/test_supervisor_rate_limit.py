from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from factories import T0
from modules.bots.domain.models import BotState
from modules.exchanges.errors import RateLimited
from modules.trading.application.supervisor import BotSupervisor


class _Clock:
    def __init__(self) -> None:
        self.current = T0

    def now(self):
        return self.current


class _Trader:
    def __init__(self) -> None:
        self.processed: list[object] = []

    async def process(self, bot) -> None:
        self.processed.append(bot.id)


def _bot():
    return SimpleNamespace(
        id=uuid4(), desired_state=BotState.RUNNING, observed_state=BotState.RUNNING, config=None
    )


def _supervisor(clock: _Clock, trader: _Trader) -> BotSupervisor:
    supervisor = BotSupervisor(None, trader, None, clock, None)  # type: ignore[arg-type]
    supervisor._mode_problem = lambda bot: None  # type: ignore[method-assign]
    return supervisor


@pytest.mark.asyncio
async def test_a_429_pauses_every_bot_for_retry_after_and_is_not_counted_as_a_failure() -> None:
    clock, trader = _Clock(), _Trader()
    supervisor = _supervisor(clock, trader)
    first, second = _bot(), _bot()

    await supervisor._on_failure(first, RateLimited("429", 30))

    assert supervisor._failures == {}  # never pushes the bot toward the ERROR state
    await supervisor._handle(second)
    assert trader.processed == []  # another bot waits too: the limit is per IP

    clock.current += timedelta(seconds=29)
    await supervisor._handle(second)
    assert trader.processed == []

    clock.current += timedelta(seconds=2)
    await supervisor._handle(second)
    assert trader.processed == [second.id]


@pytest.mark.asyncio
async def test_a_429_without_retry_after_waits_a_minute_and_never_shortens_a_longer_wait() -> None:
    clock, trader = _Clock(), _Trader()
    supervisor = _supervisor(clock, trader)
    bot = _bot()

    await supervisor._on_failure(bot, RateLimited("418 banned", 300))
    await supervisor._on_failure(bot, RateLimited("429"))  # no Retry-After

    assert supervisor._rate_limited_until == T0 + timedelta(seconds=300)
