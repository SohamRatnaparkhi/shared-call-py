"""Benchmark with realistic database contention."""

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


class SimulatedDatabase:
    """Simulates a database that slows down under concurrent load."""

    def __init__(self, max_concurrent: int = 10):
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.active_queries = 0
        self.lock = asyncio.Lock()
        self.total_queries = 0

    async def query(self, resource_id: int) -> dict:
        """Execute query with realistic latency degradation."""
        async with self.lock:
            self.active_queries += 1
            self.total_queries += 1
            current_load = self.active_queries

        # Latency increases with concurrent queries (realistic!)
        base_latency = 0.05  # 50ms baseline
        contention_penalty = current_load * 0.01  # +10ms per concurrent query
        total_latency = base_latency + contention_penalty

        # Simulate connection pool exhaustion
        async with self.semaphore:  # Only N concurrent queries allowed
            await asyncio.sleep(total_latency)
            result = {
                "id": resource_id,
                "data": f"Resource {resource_id}",
                "query_latency_ms": total_latency * 1000,
            }

        async with self.lock:
            self.active_queries -= 1

        return result


@dataclass
class BenchmarkResult:
    duration_seconds: float
    concurrent_requests: int
    actual_executions: int
    coalescing_rate: float
    avg_latency_ms: float
    p99_latency_ms: float


async def benchmark_without_coalescing(
    num_requests: int, resource_id: int, db: SimulatedDatabase
) -> BenchmarkResult:
    """Benchmark without coalescing - database gets hammered."""
    latencies = []

    async def worker():
        start = time.perf_counter()
        await db.query(resource_id)
        latency = (time.perf_counter() - start) * 1000
        latencies.append(latency)

    start = time.perf_counter()
    tasks = [asyncio.create_task(worker()) for _ in range(num_requests)]
    await asyncio.gather(*tasks)
    duration = time.perf_counter() - start

    latencies.sort()
    p99_index = int(len(latencies) * 0.99)

    return BenchmarkResult(
        duration_seconds=duration,
        concurrent_requests=num_requests,
        actual_executions=db.total_queries,
        coalescing_rate=0.0,
        avg_latency_ms=sum(latencies) / len(latencies),
        p99_latency_ms=latencies[p99_index],
    )


async def benchmark_with_coalescing(
    num_requests: int, resource_id: int, db: SimulatedDatabase
) -> BenchmarkResult:
    """Benchmark with coalescing - database protected."""
    shared = AsyncSharedCall()
    latencies = []

    @shared.group()
    async def get_resource(rid: int) -> dict:
        return await db.query(rid)

    async def worker():
        start = time.perf_counter()
        await get_resource(resource_id)
        latency = (time.perf_counter() - start) * 1000
        latencies.append(latency)

    start = time.perf_counter()
    tasks = [asyncio.create_task(worker()) for _ in range(num_requests)]
    await asyncio.gather(*tasks)
    duration = time.perf_counter() - start

    stats = await shared.get_stats()
    latencies.sort()
    p99_index = int(len(latencies) * 0.99)

    return BenchmarkResult(
        duration_seconds=duration,
        concurrent_requests=num_requests,
        actual_executions=stats.misses,
        coalescing_rate=stats.hit_rate,
        avg_latency_ms=sum(latencies) / len(latencies),
        p99_latency_ms=latencies[p99_index],
    )


def print_results(name: str, result: BenchmarkResult):
    print(f"\n{'=' * 70}")
    print(f"{name}")
    print(f"{'=' * 70}")
    print(f"Concurrent Requests:   {result.concurrent_requests:,}")
    print(f"Actual DB Queries:     {result.actual_executions:,}")
    print(f"Coalescing Rate:       {result.coalescing_rate * 100:.1f}%")
    print(f"Total Duration:        {result.duration_seconds:.3f}s")
    print(f"Avg Latency:           {result.avg_latency_ms:.2f}ms")
    print(f"p99 Latency:           {result.p99_latency_ms:.2f}ms")


async def main():
    print("\n🚀 Realistic Database Load Benchmark")
    print("Scenario: Database with 10 connection pool limit")
    print("         Latency degrades: 50ms base + 10ms per concurrent query\n")

    num_requests = 100
    resource_id = 42

    # Without coalescing - fresh DB
    db_without = SimulatedDatabase(max_concurrent=10)
    print("⏱️  Running WITHOUT coalescing...")
    result_without = await benchmark_without_coalescing(num_requests, resource_id, db_without)
    print_results("❌ WITHOUT Request Coalescing", result_without)

    # With coalescing - fresh DB
    db_with = SimulatedDatabase(max_concurrent=10)
    print("\n⏱️  Running WITH coalescing...")
    result_with = await benchmark_with_coalescing(num_requests, resource_id, db_with)
    print_results("✅ WITH Request Coalescing", result_with)

    # Calculate improvement
    print(f"\n{'=' * 70}")
    print("📊 PERFORMANCE IMPROVEMENT")
    print(f"{'=' * 70}")

    speedup = result_without.duration_seconds / result_with.duration_seconds
    latency_improvement = result_without.avg_latency_ms / result_with.avg_latency_ms
    p99_improvement = result_without.p99_latency_ms / result_with.p99_latency_ms

    print(f"Total Speedup:         {speedup:.1f}x faster")
    print(f"Avg Latency:           {latency_improvement:.1f}x faster")
    print(f"p99 Latency:           {p99_improvement:.1f}x faster")
    print(
        f"DB Queries Eliminated: {result_without.actual_executions - result_with.actual_executions:,}"
    )
    print(
        f"Load Reduction:        {(1 - result_with.actual_executions / result_without.actual_executions) * 100:.1f}%"
    )
    print()


if __name__ == "__main__":
    asyncio.run(main())
