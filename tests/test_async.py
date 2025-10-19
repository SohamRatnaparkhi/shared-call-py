import asyncio

import pytest

from src._async import AsyncSharedCall


@pytest.mark.asyncio
async def test_async_group_coalesces_concurrent_requests():
    shared = AsyncSharedCall()
    call_count = 0
    call_lock = asyncio.Lock()
    task_count = 6
    start = asyncio.Event()

    @shared.group()
    async def heavy(value: int) -> int:
        nonlocal call_count
        async with call_lock:
            call_count += 1
        await asyncio.sleep(0.05)
        return value * 2

    async def worker() -> int:
        await start.wait()
        return await heavy(21)

    tasks = [asyncio.create_task(worker()) for _ in range(task_count)]
    await asyncio.sleep(0)
    start.set()
    results = await asyncio.gather(*tasks)

    assert len(results) == task_count
    assert set(results) == {42}
    assert call_count == 1

    stats = await shared.get_stats()
    assert stats.hits == task_count - 1
    assert stats.misses == 1
    assert stats.errors == 0
    assert stats.in_flight == 0


@pytest.mark.asyncio
async def test_async_reset_stats():
    shared = AsyncSharedCall()

    @shared.group()
    async def identity(value: int) -> int:
        return value

    assert await identity(5) == 5
    stats = await shared.get_stats()
    assert stats.misses == 1
    assert stats.hits == 0

    await shared.reset_stats()
    reset = await shared.get_stats()
    assert reset.misses == 0
    assert reset.hits == 0
    assert reset.errors == 0
    assert reset.in_flight == 0


@pytest.mark.asyncio
async def test_async_forget_prevents_coalescing():
    shared = AsyncSharedCall()
    call_count = 0
    call_lock = asyncio.Lock()

    @shared.group(key_fn=lambda x: "fixed_key")
    async def tracked(value: int) -> int:
        nonlocal call_count
        async with call_lock:
            call_count += 1
        await asyncio.sleep(0.05)
        return value

    # First call
    result1 = await tracked(10)
    assert result1 == 10
    assert call_count == 1

    # Start a long-running call in background
    task1 = asyncio.create_task(tracked(20))
    await asyncio.sleep(0.01)

    # Forget the key while background call is in-flight
    await shared.forget("fixed_key")

    # This call should NOT coalesce with the in-flight call
    result2 = await tracked(30)

    # Wait for background task
    result1_bg = await task1

    # Background call should have returned its value
    assert result1_bg == 20
    # New call after forget should have executed independently
    assert result2 == 30
    # We should have 3 total executions (not 2 if it had coalesced)
    assert call_count == 3
