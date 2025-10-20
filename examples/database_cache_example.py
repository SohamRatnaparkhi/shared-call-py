"""Real-world example: Database query coalescing with cache invalidation.

Demonstrates how to use SharedCall with a database ORM to prevent duplicate
queries during high-traffic scenarios, with cache invalidation on updates.
"""

import threading
import time
from typing import Optional

from shared_call_py import SharedCall


# Simulate a simple database
class Database:
    """Mock database with query latency."""

    def __init__(self):
        self.data = {
            1: {"id": 1, "name": "Alice", "email": "alice@example.com", "age": 30},
            2: {"id": 2, "name": "Bob", "email": "bob@example.com", "age": 25},
            3: {"id": 3, "name": "Charlie", "email": "charlie@example.com", "age": 35},
        }
        self.query_count = 0
        self.lock = threading.Lock()

    def query_user(self, user_id: int) -> Optional[dict]:
        """Simulate expensive database query."""
        with self.lock:
            self.query_count += 1
            print(f"🔍 DB Query #{self.query_count}: Fetching user {user_id}")

        time.sleep(0.1)  # Simulate query latency
        return self.data.get(user_id)

    def update_user(self, user_id: int, updates: dict) -> bool:
        """Update user record in database."""
        with self.lock:
            if user_id in self.data:
                self.data[user_id].update(updates)
                print(f"✏️  DB Update: User {user_id} updated with {updates}")
                return True
            return False


class UserRepository:
    """Repository pattern with request coalescing."""

    def __init__(self, db: Database):
        self.db = db
        self.shared = SharedCall()

    def get_user(self, user_id: int) -> Optional[dict]:
        """Get user with automatic request coalescing.

        Multiple concurrent calls for the same user_id will share a single query.
        """
        return self._get_user_internal(user_id)

    @property
    def _get_user_internal(self):
        """Internal method decorated with coalescing."""
        if not hasattr(self, "_cached_get_user"):

            @self.shared.group(key_fn=lambda uid: f"user:{uid}")
            def get_user_impl(user_id: int) -> Optional[dict]:
                return self.db.query_user(user_id)

            self._cached_get_user = get_user_impl
        return self._cached_get_user

    def update_user(self, user_id: int, updates: dict) -> bool:
        """Update user and invalidate coalescing cache."""
        success = self.db.update_user(user_id, updates)

        if success:
            # Invalidate cache so next query fetches fresh data
            cache_key = f"user:{user_id}"
            self.shared.forget(cache_key)
            print(f"🗑️  Cache invalidated for {cache_key}")

        return success

    def get_stats(self):
        """Get coalescing statistics."""
        return self.shared.get_stats()


def simulate_high_traffic_scenario():
    """Simulate realistic high-traffic web application scenario."""
    print("\n" + "=" * 70)
    print("🌐 SCENARIO: High-Traffic Web Application")
    print("=" * 70)
    print("100 concurrent requests for user profiles during page load")
    print()

    db = Database()
    repo = UserRepository(db)

    # Simulate 100 concurrent requests for 3 different users
    barrier = threading.Barrier(100)
    results = []
    results_lock = threading.Lock()

    def handle_request(user_id: int):
        """Simulate a web request handler."""
        barrier.wait()  # Start all threads simultaneously
        user = repo.get_user(user_id)
        with results_lock:
            results.append(user)

    # Create 100 concurrent requests
    # 50 for user 1, 30 for user 2, 20 for user 3
    threads = []
    threads.extend([threading.Thread(target=handle_request, args=(1,)) for _ in range(50)])
    threads.extend([threading.Thread(target=handle_request, args=(2,)) for _ in range(30)])
    threads.extend([threading.Thread(target=handle_request, args=(3,)) for _ in range(20)])

    print("🚀 Starting 100 concurrent requests...")
    start = time.perf_counter()

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    duration = time.perf_counter() - start

    # Print results
    stats = repo.get_stats()
    print(f"\n✅ All requests completed in {duration:.3f}s")
    print(f"\n📊 RESULTS:")
    print(f"   Total Requests:        100")
    print(f"   Actual DB Queries:     {db.query_count}")
    print(f"   Queries Saved:         {100 - db.query_count}")
    print(f"   Coalescing Rate:       {stats.hit_rate * 100:.1f}%")
    print(f"   Efficiency Gain:       {(100 - db.query_count) / 100 * 100:.1f}% reduction in DB load")


def simulate_cache_invalidation_scenario():
    """Demonstrate cache invalidation on data updates."""
    print("\n" + "=" * 70)
    print("🔄 SCENARIO: Cache Invalidation on Update")
    print("=" * 70)
    print()

    db = Database()
    repo = UserRepository(db)

    # First batch: concurrent reads
    print("Phase 1: 50 concurrent reads for user 1")
    barrier = threading.Barrier(50)

    def read_user():
        barrier.wait()
        repo.get_user(1)

    threads = [threading.Thread(target=read_user) for _ in range(50)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    stats_after_reads = repo.get_stats()
    print(f"✅ DB Queries: {db.query_count} (should be 1)")

    # Update user
    print("\nPhase 2: Update user 1")
    repo.update_user(1, {"age": 31, "email": "alice.new@example.com"})

    # Second batch: concurrent reads after update
    print("\nPhase 3: 50 concurrent reads for user 1 (after update)")
    barrier2 = threading.Barrier(50)

    def read_user_after_update():
        barrier2.wait()
        user = repo.get_user(1)
        assert user["age"] == 31  # Should get updated data

    threads2 = [threading.Thread(target=read_user_after_update) for _ in range(50)]
    for t in threads2:
        t.start()
    for t in threads2:
        t.join()

    print(f"\n✅ DB Queries: {db.query_count} (should be 2 - one before update, one after)")
    print(f"✅ All readers received updated data!")

    stats_final = repo.get_stats()
    print(f"\n📊 FINAL STATS:")
    print(f"   Total Requests:        100")
    print(f"   Actual DB Queries:     {db.query_count}")
    print(f"   Coalescing Rate:       {stats_final.hit_rate * 100:.1f}%")


def main():
    """Run all scenarios."""
    simulate_high_traffic_scenario()
    simulate_cache_invalidation_scenario()
    print("\n" + "=" * 70)
    print("✨ Demo complete!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
