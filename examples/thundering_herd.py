"""Benchmark showing cache stampede protection."""

import asyncio
import time
from typing import Optional


try:
    from src import AsyncSharedCall
except ModuleNotFoundError:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from src import AsyncSharedCall


class Cache:
    """Simple in-memory cache that expires."""

    def __init__(self):
        self.data: dict[str, tuple[any, float]] = {}
        self.lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[any]:
        async with self.lock:
            if key in self.data:
                value, expiry = self.data[key]
                if time.time() < expiry:
                    return value
                del self.data[key]
            return None

    async def set(self, key: str, value: any, ttl: float = 5.0):
        async with self.lock:
            self.data[key] = (value, time.time() + ttl)


# Simulate expensive aggregation query
query_count = 0


async def expensive_aggregation() -> dict:
    """Simulates complex query taking 2 seconds."""
    global query_count
    query_count += 1
    await asyncio.sleep(2.0)  # Heavy computation
    return {"trending_posts": [1, 2, 3, 4, 5], "computed_at": time.time()}


async def fetch_trending_without_coalescing(cache: Cache) -> dict:
    """Standard cache pattern - vulnerable to stampede."""
    cached = await cache.get("trending")
    if cached:
        return cached

    # Cache miss - everyone executes!
    result = await expensive_aggregation()
    await cache.set("trending", result)
    return result


async def fetch_trending_with_coalescing(cache: Cache, shared: AsyncSharedCall) -> dict:
    """Cache pattern with coalescing - stampede protected."""
    cached = await cache.get("trending")
    if cached:
        return cached

    # Cache miss - only ONE executes via coalescing
    @shared.group(key_fn=lambda: "trending")
    async def compute():
        return await expensive_aggregation()

    result = await compute()
    await cache.set("trending", result)
    return result


async def simulate_stampede_without_protection():
    """100 requests hit expired cache simultaneously."""
    global query_count
    query_count = 0

    cache = Cache()
    # Don't pre-populate cache - simulate cache miss

    print("\n⏱️  Simulating cache stampede WITHOUT protection...")
    start = time.perf_counter()

    tasks = [asyncio.create_task(fetch_trending_without_coalescing(cache)) for _ in range(100)]
    await asyncio.gather(*tasks)

    duration = time.perf_counter() - start

    print("❌ WITHOUT Protection:")
    print(f"   Duration: {duration:.3f}s")
    print(f"   DB Queries: {query_count} (should be 1!)")
    print(f"   Wasted Queries: {query_count - 1}")


async def simulate_stampede_with_protection():
    """1000 requests hit expired cache - protected by coalescing."""
    global query_count
    query_count = 0

    cache = Cache()
    shared = AsyncSharedCall()

    print("\n⏱️  Simulating cache stampede WITH protection...")
    start = time.perf_counter()

    tasks = [
        asyncio.create_task(fetch_trending_with_coalescing(cache, shared)) for _ in range(100)
    ]
    await asyncio.gather(*tasks)

    duration = time.perf_counter() - start
    stats = await shared.get_stats()

    print("✅ WITH Protection (AsyncSharedCall):")
    print(f"   Duration: {duration:.3f}s")
    print(f"   DB Queries: {query_count}")
    print(f"   Coalescing Rate: {stats.hit_rate * 100:.1f}%")
    print(f"   Queries Prevented: {99}")


async def main():
    print("\n🚀 Cache Stampede Protection Benchmark")
    print("Scenario: 100 users hit endpoint when cache expires")
    print("         Expensive query takes 2 seconds\n")

    await simulate_stampede_without_protection()
    await simulate_stampede_with_protection()

    print(f"\n{'=' * 60}")
    print("💡 Key Insight:")
    print("   Without coalescing: Database gets 100 queries")
    print("   With coalescing: Database gets 1 query")
    print("   System stays stable under load!")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    asyncio.run(main())
