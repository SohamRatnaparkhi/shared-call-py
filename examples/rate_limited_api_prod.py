"""Real-world example: Rate-limited API client with request coalescing.

Demonstrates how AsyncSharedCall prevents hitting API rate limits when multiple
parts of your application request the same resource simultaneously.
"""

import asyncio
import time
from dataclasses import dataclass


try:
    from src import AsyncSharedCall
except ModuleNotFoundError:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from src import AsyncSharedCall


@dataclass
class RateLimitError(Exception):
    """Raised when API rate limit is exceeded."""

    message: str


class RateLimitedAPIClient:
    """Mock external API with strict rate limiting."""

    def __init__(self, rate_limit: int = 10, window_seconds: float = 1.0):
        """Initialize API client with rate limiting.

        Args:
            rate_limit: Maximum requests allowed per window.
            window_seconds: Time window for rate limiting.
        """
        self.rate_limit = rate_limit
        self.window_seconds = window_seconds
        self.request_timestamps: list[float] = []
        self.lock = asyncio.Lock()
        self.total_requests = 0

    async def _check_rate_limit(self):
        """Check if request would exceed rate limit."""
        now = time.time()
        cutoff = now - self.window_seconds

        # Remove old timestamps
        self.request_timestamps = [ts for ts in self.request_timestamps if ts > cutoff]

        if len(self.request_timestamps) >= self.rate_limit:
            raise RateLimitError(
                f"Rate limit exceeded: {self.rate_limit} requests per {self.window_seconds}s"
            )

        self.request_timestamps.append(now)
        self.total_requests += 1

    async def fetch_user(self, user_id: int) -> dict:
        """Fetch user from API (rate limited)."""
        async with self.lock:
            await self._check_rate_limit()
            print(f"🌐 API Request #{self.total_requests}: Fetching user {user_id}")

        # Simulate network latency
        await asyncio.sleep(0.05)

        return {
            "id": user_id,
            "username": f"user_{user_id}",
            "profile": f"Profile for user {user_id}",
            "followers": user_id * 100,
        }

    async def fetch_post(self, post_id: int) -> dict:
        """Fetch post from API (rate limited)."""
        async with self.lock:
            await self._check_rate_limit()
            print(f"🌐 API Request #{self.total_requests}: Fetching post {post_id}")

        await asyncio.sleep(0.05)

        return {
            "id": post_id,
            "title": f"Post {post_id}",
            "content": f"Content for post {post_id}",
            "likes": post_id * 10,
        }


class SmartAPIClient:
    """API client wrapper with request coalescing to prevent rate limit issues."""

    def __init__(self, api_client: RateLimitedAPIClient):
        self.api = api_client
        self.shared = AsyncSharedCall()

    async def get_user(self, user_id: int) -> dict:
        """Get user with automatic request deduplication."""
        return await self._fetch_user(user_id)

    async def get_post(self, post_id: int) -> dict:
        """Get post with automatic request deduplication."""
        return await self._fetch_post(post_id)

    @property
    def _fetch_user(self):
        """Internal user fetcher with coalescing."""
        if not hasattr(self, "_cached_fetch_user"):

            @self.shared.group(key_fn=lambda uid: f"user:{uid}")
            async def fetch_impl(user_id: int) -> dict:
                return await self.api.fetch_user(user_id)

            self._cached_fetch_user = fetch_impl
        return self._cached_fetch_user

    @property
    def _fetch_post(self):
        """Internal post fetcher with coalescing."""
        if not hasattr(self, "_cached_fetch_post"):

            @self.shared.group(key_fn=lambda pid: f"post:{pid}")
            async def fetch_impl(post_id: int) -> dict:
                return await self.api.fetch_post(post_id)

            self._cached_fetch_post = fetch_impl
        return self._cached_fetch_post

    async def get_stats(self):
        """Get coalescing statistics."""
        return await self.shared.get_stats()


async def scenario_without_coalescing():
    """Demonstrate rate limit issues without coalescing."""
    print("\n" + "=" * 70)
    print("❌ SCENARIO 1: WITHOUT Request Coalescing (Will Hit Rate Limit)")
    print("=" * 70)
    print("API Rate Limit: 10 requests/second")
    print("Making 50 concurrent requests for user 1...")
    print()

    api = RateLimitedAPIClient(rate_limit=10, window_seconds=1.0)

    try:
        tasks = [api.fetch_user(1) for _ in range(50)]
        await asyncio.gather(*tasks)
        print("✅ Success (unexpected!)")
    except RateLimitError as e:
        print(f"💥 FAILED: {e.message}")
        print(f"📊 API Requests Made: {api.total_requests}")
        print("⚠️  Application needs to implement retry logic and backoff!")


async def scenario_with_coalescing():
    """Demonstrate successful operation with coalescing."""
    print("\n" + "=" * 70)
    print("✅ SCENARIO 2: WITH Request Coalescing (SmartAPIClient)")
    print("=" * 70)
    print("API Rate Limit: 10 requests/second")
    print("Making 50 concurrent requests for user 1...")
    print()

    api = RateLimitedAPIClient(rate_limit=10, window_seconds=1.0)
    client = SmartAPIClient(api)

    start = time.perf_counter()

    try:
        tasks = [client.get_user(1) for _ in range(50)]
        _results = await asyncio.gather(*tasks)
        duration = time.perf_counter() - start

        print("✅ SUCCESS: All 50 requests completed!")
        print("📊 RESULTS:")
        print("   Total Requests:        50")
        print(f"   Actual API Calls:      {api.total_requests}")
        print(f"   Requests Saved:        {50 - api.total_requests}")
        print(f"   Duration:              {duration:.3f}s")
        print("   No rate limit errors! 🎉")

        stats = await client.get_stats()
        print("\n   Coalescing Stats:")
        print(f"   - Hits (coalesced):    {stats.hits}")
        print(f"   - Misses (executed):   {stats.misses}")
        print(f"   - Hit Rate:            {stats.hit_rate * 100:.1f}%")

    except RateLimitError as e:
        print(f"💥 FAILED: {e.message}")


async def scenario_mixed_workload():
    """Realistic scenario with mixed requests."""
    print("\n" + "=" * 70)
    print("🎯 SCENARIO 3: Realistic Mixed Workload")
    print("=" * 70)
    print("Simulating microservice handling diverse requests")
    print("API Rate Limit: 10 requests/second")
    print()

    api = RateLimitedAPIClient(rate_limit=10, window_seconds=1.0)
    client = SmartAPIClient(api)

    # Simulate diverse workload:
    # - Multiple services requesting same users
    # - Dashboard loading multiple resources
    # - Background jobs fetching data

    async def service_a():
        """Service A needs user 1, 2, 3 repeatedly."""
        return await asyncio.gather(*[client.get_user(i % 3 + 1) for i in range(20)])

    async def service_b():
        """Service B needs posts 1, 2 repeatedly."""
        return await asyncio.gather(*[client.get_post(i % 2 + 1) for i in range(15)])

    async def dashboard():
        """Dashboard loads various resources."""
        users = await asyncio.gather(*[client.get_user(i) for i in range(1, 4)])
        posts = await asyncio.gather(*[client.get_post(i) for i in range(1, 3)])
        return users + posts

    start = time.perf_counter()

    try:
        # Run all workloads concurrently
        await asyncio.gather(service_a(), service_b(), dashboard(), dashboard())

        duration = time.perf_counter() - start
        stats = await client.get_stats()

        total_requested = 20 + 15 + 5 + 5  # service_a + service_b + 2 dashboards
        actual_calls = api.total_requests

        print("✅ SUCCESS: All services completed!")
        print("\n📊 COMPREHENSIVE RESULTS:")
        print(f"   Total Requests:        {total_requested}")
        print(f"   Actual API Calls:      {actual_calls}")
        print(f"   Requests Saved:        {total_requested - actual_calls}")
        print(f"   Efficiency:            {(1 - actual_calls / total_requested) * 100:.1f}% reduction")
        print(f"   Duration:              {duration:.3f}s")
        print("   Rate Limit Status:     ✅ No violations")
        print("\n   Coalescing Stats:")
        print(f"   - Total Hits:          {stats.hits}")
        print(f"   - Total Misses:        {stats.misses}")
        print(f"   - Hit Rate:            {stats.hit_rate * 100:.1f}%")
        print(f"   - Errors:              {stats.errors}")

    except RateLimitError as e:
        print(f"💥 FAILED: {e.message}")


async def main():
    """Run all scenarios."""
    await scenario_without_coalescing()
    await scenario_with_coalescing()
    await scenario_mixed_workload()

    print("\n" + "=" * 70)
    print("✨ Demo complete!")
    print("=" * 70)
    print("\n💡 Key Takeaways:")
    print("   1. Request coalescing prevents rate limit violations")
    print("   2. Reduces load on external APIs by 90%+ in high-traffic scenarios")
    print("   3. Improves response times for concurrent identical requests")
    print("   4. No code changes needed in service logic - just wrap the client!")
    print()


if __name__ == "__main__":
    asyncio.run(main())
