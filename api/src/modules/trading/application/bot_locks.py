"""Serialize everything that changes one bot's orders, position or stop.

The supervisor (sending orders) and the private-stream monitor (settling fills, syncing stops,
reconciling the account) run as separate tasks of the same worker. Without a lock, a fill event
can arrive while an entry is still being sent, so the same fill is applied twice or the account
reconciler sees an "unresolved" order and pauses every bot of the connection.

The lock is per bot and per event loop, and *re-entrant for the task that holds it*: public
OrderExecutor methods call each other (submit -> ensure_native_stop -> ...), so only the
outermost call really waits. Several bots are always taken in ascending id order.
"""

import asyncio
import weakref
from collections.abc import AsyncIterator, Iterable
from contextlib import asynccontextmanager
from contextvars import ContextVar
from uuid import UUID

_LOCKS: "weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, dict[UUID, asyncio.Lock]]" = (
    weakref.WeakKeyDictionary()
)
_HELD: ContextVar[frozenset[UUID]] = ContextVar("held_bot_locks", default=frozenset())


def _lock_for(bot_id: UUID) -> asyncio.Lock:
    locks = _LOCKS.setdefault(asyncio.get_running_loop(), {})
    return locks.setdefault(bot_id, asyncio.Lock())


@asynccontextmanager
async def hold_bots(bot_ids: Iterable[UUID]) -> AsyncIterator[None]:
    """Hold the locks of ``bot_ids`` (those this task already holds are not taken again)."""
    held = _HELD.get()
    wanted = sorted(set(bot_ids) - held, key=lambda value: value.int)
    acquired: list[asyncio.Lock] = []
    try:
        for bot_id in wanted:
            lock = _lock_for(bot_id)
            await lock.acquire()
            acquired.append(lock)
        token = _HELD.set(held | set(wanted))
        try:
            yield
        finally:
            _HELD.reset(token)
    finally:
        for lock in reversed(acquired):
            lock.release()
