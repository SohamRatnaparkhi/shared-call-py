"""Benchmark demonstrating sync request coalescing performance gains.

Simulates a database query scenario where 1000 concurrent threads request
the same user record. Shows dramatic reduction in actual database calls.
"""

import threading
import time
from dataclasses import dataclass


try:
    from src import SharedCall
except ModuleNotFoundError:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

    from src import SharedCall


@dataclass
class BenchmarkResult:
    """Performance metrics for a benchmark run."""

    duration_seconds: float
    concurrent_requests: int
    actual_executions: int
    coalescing_rate: float


# Simulate expensive database query
def simulate_db_query(user_id: int) -> dict:
    """Mock database query with 50ms latency."""
    time.sleep(1)  # Simulate network + query time
    return {"id": user_id, "name": f"User {user_id}", "email": f"user{user_id}@example.com"}


def benchmark_without_coalescing(num_requests: int, user_id: int) -> BenchmarkResult:
    """Benchmark without any request deduplication."""
    execution_count = 0
    execution_lock = threading.Lock()
    barrier = threading.Barrier(num_requests)

    def worker():
        nonlocal execution_count
        barrier.wait()
        simulate_db_query(user_id)
        with execution_lock:
            execution_count += 1

    start = time.perf_counter()

    threads = [threading.Thread(target=worker) for _ in range(num_requests)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    duration = time.perf_counter() - start

    return BenchmarkResult(
        duration_seconds=duration,
        concurrent_requests=num_requests,
        actual_executions=execution_count,
        coalescing_rate=0.0,
    )


def benchmark_with_coalescing(num_requests: int, user_id: int) -> BenchmarkResult:
    """Benchmark with SharedCall request deduplication."""
    shared = SharedCall()

    @shared.group()
    def get_user(uid: int) -> dict:
        return simulate_db_query(uid)

    barrier = threading.Barrier(num_requests)

    def worker():
        barrier.wait()
        get_user(user_id)

    start = time.perf_counter()

    threads = [threading.Thread(target=worker) for _ in range(num_requests)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    duration = time.perf_counter() - start
    stats = shared.get_stats()

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


def main():
    """Run comprehensive benchmarks comparing with/without coalescing."""
    print("\n🚀 Shared Call Synchronous Benchmark")
    print("Scenario: 1000 threads requesting the same user record")
    print("Simulated DB query latency: 50ms")

    num_requests = 1000
    user_id = 42

    print("\n⏱️  Running benchmarks...")

    # Without coalescing
    result_without = benchmark_without_coalescing(num_requests, user_id)
    print_results("❌ WITHOUT Request Coalescing", result_without)

    # With coalescing
    result_with = benchmark_with_coalescing(num_requests, user_id)
    print_results("✅ WITH Request Coalescing (SharedCall)", result_with)

    # Calculate improvement
    print(f"\n{'=' * 60}")
    print("📊 PERFORMANCE IMPROVEMENT")
    print(f"{'=' * 60}")

    speedup = result_without.duration_seconds / result_with.duration_seconds
    time_saved = result_without.duration_seconds - result_with.duration_seconds
    db_calls_saved = result_without.actual_executions - result_with.actual_executions

    print(f"Speedup:               {speedup:.1f}x faster")
    print(f"Time Saved:            {time_saved:.3f}s ({time_saved / result_without.duration_seconds * 100:.1f}%)")
    print(f"DB Calls Eliminated:   {db_calls_saved:,} / {result_without.actual_executions:,}")
    print(f"Load Reduction:        {db_calls_saved / result_without.actual_executions * 100:.1f}%")
    print()


if __name__ == "__main__":
    main()
