"""Benchmark demonstrating async request coalescing performance gains.

Simulates an API call scenario where 1000 concurrent coroutines request
the same resource. Shows dramatic reduction in actual API calls.
"""

import asyncio
import time
from dataclasses import dataclass

from shared_call_py import AsyncSharedCall


@dataclass
class BenchmarkResult:
    """Performance metrics for a benchmark run."""

    duration_seconds: float
    concurrent_requests: int
    actual_executions: int
    coalescing_rate: float


# Simulate expensive API call
async def simulate_api_call(resource_id: int) -> dict:
    """Mock external API call with 50ms latency."""
    await asyncio.sleep(1)  # Simulate network latency
    return {
        "id": resource_id,
        "title": f"Resource {resource_id}",
        "data": f"Content for resource {resource_id}",
    }


async def benchmark_without_coalescing(num_requests: int, resource_id: int) -> BenchmarkResult:
    """Benchmark without any request deduplication."""
    execution_count = 0
    execution_lock = asyncio.Lock()

    async def worker():
        nonlocal execution_count
        await simulate_api_call(resource_id)
        async with execution_lock:
            execution_count += 1

    start = time.perf_counter()

    tasks = [asyncio.create_task(worker()) for _ in range(num_requests)]
    await asyncio.gather(*tasks)

    duration = time.perf_counter() - start

    return BenchmarkResult(
        duration_seconds=duration,
        concurrent_requests=num_requests,
        actual_executions=execution_count,
        coalescing_rate=0.0,
    )


async def benchmark_with_coalescing(num_requests: int, resource_id: int) -> BenchmarkResult:
    """Benchmark with AsyncSharedCall request deduplication."""
    shared = AsyncSharedCall()

    @shared.group()
    async def get_resource(rid: int) -> dict:
        return await simulate_api_call(rid)

    start = time.perf_counter()

    tasks = [asyncio.create_task(get_resource(resource_id)) for _ in range(num_requests)]
    await asyncio.gather(*tasks)

    duration = time.perf_counter() - start
    stats = await shared.get_stats()

    return BenchmarkResult(
        duration_seconds=duration,
        concurrent_requests=num_requests,
        actual_executions=stats.misses,
        coalescing_rate=stats.hit_rate,
    )


def print_results(name: str, result: BenchmarkResult):
    """Pretty print benchmark results."""
    print(f"\n{'=' * 60}")
    print(f"{name}")
    print(f"{'=' * 60}")
    print(f"Concurrent Requests:   {result.concurrent_requests:,}")
    print(f"Actual Executions:     {result.actual_executions:,}")
    print(f"Coalescing Rate:       {result.coalescing_rate * 100:.1f}%")
    print(f"Total Duration:        {result.duration_seconds:.3f}s")
    print(f"Avg per Request:       {result.duration_seconds / result.concurrent_requests * 1000:.2f}ms")


async def main():
    """Run comprehensive benchmarks comparing with/without coalescing."""
    print("\n🚀 Shared Call Async Benchmark")
    print("Scenario: 1000 concurrent coroutines requesting the same resource")
    print("Simulated API call latency: 50ms")

    num_requests = 1000
    resource_id = 42

    print("\n⏱️  Running benchmarks...")

    # Without coalescing
    result_without = await benchmark_without_coalescing(num_requests, resource_id)
    print_results("❌ WITHOUT Request Coalescing", result_without)

    # With coalescing
    result_with = await benchmark_with_coalescing(num_requests, resource_id)
    print_results("✅ WITH Request Coalescing (AsyncSharedCall)", result_with)

    # Calculate improvement
    print(f"\n{'=' * 60}")
    print("📊 PERFORMANCE IMPROVEMENT")
    print(f"{'=' * 60}")

    speedup = result_without.duration_seconds / result_with.duration_seconds
    time_saved = result_without.duration_seconds - result_with.duration_seconds
    api_calls_saved = result_without.actual_executions - result_with.actual_executions

    print(f"Speedup:               {speedup:.1f}x faster")
    print(f"Time Saved:            {time_saved:.3f}s ({time_saved / result_without.duration_seconds * 100:.1f}%)")
    print(f"API Calls Eliminated:  {api_calls_saved:,} / {result_without.actual_executions:,}")
    print(f"Load Reduction:        {api_calls_saved / result_without.actual_executions * 100:.1f}%")
    print()


if __name__ == "__main__":
    asyncio.run(main())
