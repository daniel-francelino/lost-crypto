import asyncio
from uuid import UUID, uuid4

import pytest

from modules.trading.application.bot_locks import hold_bots

A = UUID(int=1)
B = UUID(int=2)


async def test_same_bot_is_serialized() -> None:
    events: list[str] = []

    async def worker(name: str) -> None:
        async with hold_bots([A]):
            events.append(f"{name}:in")
            await asyncio.sleep(0.02)
            events.append(f"{name}:out")

    await asyncio.gather(worker("one"), worker("two"))

    # Never interleaved: each task leaves before the other enters.
    assert events in (
        ["one:in", "one:out", "two:in", "two:out"],
        ["two:in", "two:out", "one:in", "one:out"],
    )


async def test_different_bots_run_in_parallel() -> None:
    both_inside = asyncio.Event()
    inside: set[UUID] = set()

    async def worker(bot_id: UUID) -> None:
        async with hold_bots([bot_id]):
            inside.add(bot_id)
            if len(inside) == 2:
                both_inside.set()
            await asyncio.wait_for(both_inside.wait(), timeout=1)

    await asyncio.gather(worker(A), worker(B))

    assert inside == {A, B}


async def test_nested_holds_by_the_same_task_do_not_deadlock() -> None:
    async def inner() -> str:
        async with hold_bots([A]):  # e.g. submit() -> ensure_native_stop()
            return "done"

    async with hold_bots([A]):
        assert await asyncio.wait_for(inner(), timeout=1) == "done"


async def test_holding_several_bots_in_opposite_order_does_not_deadlock() -> None:
    async def worker(order: list[UUID]) -> None:
        async with hold_bots(order):
            await asyncio.sleep(0.01)

    await asyncio.wait_for(
        asyncio.gather(*(worker([A, B] if i % 2 else [B, A]) for i in range(20))), timeout=2
    )


async def test_lock_is_released_when_the_body_raises() -> None:
    bot_id = uuid4()
    with pytest.raises(RuntimeError):
        async with hold_bots([bot_id]):
            raise RuntimeError("boom")

    async with asyncio.timeout(1):
        async with hold_bots([bot_id]):
            pass
