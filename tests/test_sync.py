import threading
import time

from src._sync import SharedCall


def test_sync_group_coalesces_concurrent_requests():
    shared = SharedCall()
    call_count = 0
    call_count_lock = threading.Lock()
    thread_count = 6
    barrier = threading.Barrier(thread_count)
    results: list[int] = []
    results_lock = threading.Lock()

    @shared.group()
    def heavy(value: int) -> int:
        nonlocal call_count
        with call_count_lock:
            call_count += 1
        time.sleep(0.05)
        return value * 2

    def worker() -> None:
        barrier.wait()
        result = heavy(21)
        with results_lock:
            results.append(result)

    threads = [threading.Thread(target=worker) for _ in range(thread_count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(results) == thread_count
    assert set(results) == {42}
    assert call_count == 1

    stats = shared.get_stats()
    assert stats.hits == thread_count - 1
    assert stats.misses == 1
    assert stats.errors == 0
    assert stats.in_flight == 0


def test_sync_reset_stats():
    shared = SharedCall()

    @shared.group()
    def identity(value: int) -> int:
        return value

    assert identity(5) == 5
    stats = shared.get_stats()
    assert stats.misses == 1
    assert stats.hits == 0

    shared.reset_stats()
    reset = shared.get_stats()
    assert reset.misses == 0
    assert reset.hits == 0
    assert reset.errors == 0
    assert reset.in_flight == 0


def test_sync_forget_prevents_coalescing():
    shared = SharedCall()
    call_count = 0
    call_count_lock = threading.Lock()

    @shared.group(key_fn=lambda x: "fixed_key")
    def tracked(value: int) -> int:
        nonlocal call_count
        with call_count_lock:
            call_count += 1
        time.sleep(0.01)
        return value

    # First call
    result1 = tracked(10)
    assert result1 == 10
    assert call_count == 1

    # Start a long-running call in background
    barrier = threading.Barrier(2)
    result_holder = []

    def background_worker():
        barrier.wait()
        result_holder.append(tracked(20))

    bg_thread = threading.Thread(target=background_worker)
    bg_thread.start()

    # Wait for background thread to start
    barrier.wait()
    time.sleep(0.005)

    # Forget the key while background call is in-flight
    shared.forget("fixed_key")

    # This call should NOT coalesce with the in-flight call
    result3 = tracked(30)

    bg_thread.join()

    # Background call should have returned its value
    assert result_holder[0] == 20
    # New call after forget should have executed independently
    assert result3 == 30
    # We should have 3 total executions (not 2 if it had coalesced)
    assert call_count == 3
