# shared-call-py 🚀

**Eliminate redundant work and protect your systems from thundering herds with intelligent request coalescing.**

A Python implementation of request deduplication inspired by Go's `singleflight` pattern. When multiple concurrent requests ask for the same resource, only one does the actual work—everyone else gets the same result instantly.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🎯 The Problem

Modern applications face three critical challenges:

1. **Thundering Herd**: When cache expires, hundreds of requests simultaneously hammer your database
2. **Rate Limit Hell**: Concurrent identical API calls burn through your rate limits
3. **Database Overload**: High concurrency creates connection pool exhaustion and query slowdowns

**Traditional approach**: Every request executes independently—wasting resources and destabilizing systems.

**shared-call-py approach**: Coalesce duplicate in-flight requests into a single execution. The first caller becomes the "leader" and does the work. All others wait and receive the same result.

## 🚀 Real-World Impact

### Database Load Reduction
**Scenario**: 100 concurrent requests hit a database with 10 connection pool limit

```
❌ WITHOUT Request Coalescing
   Concurrent Requests:   100
   Actual DB Queries:     100
   Total Duration:        6.012s
   Avg Latency:           2232.42ms
   p99 Latency:           6010.56ms

✅ WITH Request Coalescing
   Concurrent Requests:   100
   Actual DB Queries:     1
   Total Duration:        0.065s
   Avg Latency:           60.19ms
   p99 Latency:           62.05ms

📊 PERFORMANCE IMPROVEMENT
   Total Speedup:         92.6x faster
   Avg Latency:           37.1x faster
   p99 Latency:           96.9x faster
   DB Queries Eliminated: 99
   Load Reduction:        99.0%
```

### Cache Stampede Protection
**Scenario**: 100 users hit endpoint simultaneously when cache expires

```
❌ WITHOUT Protection:
   Duration:       2.004s
   DB Queries:     100 (all 100 hit the database!)
   Wasted Queries: 99

✅ WITH Protection (AsyncSharedCall):
   Duration:       2.005s
   DB Queries:     1 (only the leader executes)
   Coalescing Rate: 99.0%
   Queries Prevented: 99

💡 System stays stable under load!
```

### Rate Limit Prevention
**Scenario**: API with 10 requests/second limit, 50 concurrent requests

```
❌ WITHOUT Coalescing:
   Successful:     10
   Failed:         90 (rate limited!)
   Error handling: Required

✅ WITH Coalescing:
   Successful:     100
   Failed:         0
   API Calls Made: 1
   API Calls Saved: 99
   Rate Limit Status: ✅ No violations
```

## 📦 Installation

```bash
pip install shared-call-py
```

Or with Poetry:
```bash
poetry add shared-call-py
```

## 🎨 Quick Start

### Async Usage (Recommended)

```python
import asyncio
from shared_call_py import AsyncSharedCall

# Create a shared call instance
shared = AsyncSharedCall()

@shared.group()
async def fetch_user(user_id: int) -> dict:
    """Expensive database query - only executes once per unique user_id"""
    print(f"🔍 Fetching user {user_id} from database...")
    await asyncio.sleep(1)  # Simulate slow query
    return {"id": user_id, "name": f"User {user_id}"}

# Simulate 100 concurrent requests for the same user
async def main():
    tasks = [fetch_user(42) for _ in range(100)]
    results = await asyncio.gather(*tasks)
    print(f"✅ Got {len(results)} results, but only 1 database query!")

asyncio.run(main())
```

**Output:**
```
🔍 Fetching user 42 from database...
✅ Got 100 results, but only 1 database query!
```

### Sync Usage

```python
from shared_call_py import SharedCall

shared = SharedCall()

@shared.group()
def expensive_operation(x: int) -> int:
    print(f"Computing {x}...")
    import time
    time.sleep(1)
    return x * 2

# Multiple threads calling simultaneously - only one executes
result = expensive_operation(5)
```

## 🏗️ Use Cases

### 1. Protect Your Database

```python
from shared_call_py import AsyncSharedCall

shared = AsyncSharedCall()

@shared.group()
async def get_user_profile(user_id: int):
    # Only one query executes, even with thousands of concurrent requests
    return await db.query("SELECT * FROM users WHERE id = ?", user_id)
```

### 2. Respect Rate Limits

```python
from shared_call_py import AsyncSharedCall

shared = AsyncSharedCall()

class APIClient:
    @shared.group()
    async def fetch_data(self, endpoint: str):
        # Multiple requests coalesce into one API call
        return await self.http_client.get(endpoint)

# 1000 concurrent requests = 1 API call (if for same endpoint)
```

### 3. Prevent Cache Stampede

```python
from shared_call_py import AsyncSharedCall

shared = AsyncSharedCall()

@shared.group()
async def get_popular_item():
    # When cache expires, only first request refills it
    result = await expensive_computation()
    cache.set("popular_item", result, ttl=300)
    return result
```

### 4. Deduplicate Background Jobs

```python
from shared_call_py import AsyncSharedCall

shared = AsyncSharedCall()

@shared.group()
async def process_webhook(webhook_id: str):
    # If duplicate webhooks arrive, only process once
    return await process_payment(webhook_id)
```

## 🎛️ Advanced Features

### Custom Key Functions

Control coalescing granularity with custom key functions:

```python
from shared_call_py import AsyncSharedCall

shared = AsyncSharedCall()

# Coalesce by user_id only, ignore other parameters
@shared.group(key_fn=lambda user_id, include_details: f"user:{user_id}")
async def fetch_user(user_id: int, include_details: bool = False):
    return await db.get_user(user_id, include_details)
```

### Statistics and Monitoring

```python
stats = await shared.get_stats()
print(f"Hit Rate: {stats.hit_rate:.1%}")
print(f"Hits: {stats.hits}")
print(f"Misses: {stats.misses}")
print(f"Errors: {stats.errors}")
print(f"Active Calls: {stats.active}")
```

### Cache Invalidation

```python
# Forget a specific key
await shared.forget("user:42")

# Clear all tracked calls
await shared.forget_all()

# Reset statistics
await shared.reset_stats()
```

## 📊 Benchmarks

See detailed benchmark results and methodologies:

- [**Database Load Benchmark**](./docs/benchmarks/database-load.md) - Connection pool exhaustion prevention
- [**Cache Stampede Benchmark**](./docs/benchmarks/cache-stampede.md) - Thundering herd protection
- [**Rate Limit Benchmark**](./docs/benchmarks/rate-limits.md) - API quota preservation

Run benchmarks yourself:
```bash
python examples/mock_db_query.py
python examples/thundering_herd.py
python examples/ratelimit.py
```

## 📚 Documentation

- [**Quick Start Guide**](./docs/quickstart.md) - Get started in 5 minutes
- [**API Reference**](./docs/api-reference.md) - Complete API documentation
- [**Benchmarks**](./docs/benchmarks/) - Performance comparisons
- [**Examples**](./examples/) - Real-world usage patterns

## 🔧 How It Works

1. **First Request**: Becomes the "leader" and executes the function
2. **Concurrent Requests**: Wait for the leader's result via `asyncio.Event` or `threading.Event`
3. **Result Sharing**: All waiters receive the same result (or error)
4. **Cleanup**: Call completes, resources released

Key features:
- **Thread-safe** and **async-safe**
- **Automatic key generation** from function name and arguments
- **Error propagation** - all waiters receive the same exception
- **Zero dependencies** - uses only Python standard library

## 🤝 When NOT to Use

- **Mutations**: Don't coalesce write operations (POST, PUT, DELETE)
- **User-specific data**: Each user needs their own result
- **Time-sensitive**: When staleness matters (though you can `forget()` keys)
- **Side effects**: Functions with important side effects beyond the return value

## 🛠️ Development

```bash
# Clone the repository
git clone https://github.com/yourusername/shared-call-py.git
cd shared-call-py

# Install dependencies
poetry install

# Run tests
poetry run pytest

# Run benchmarks
python examples/mock_db_query.py
```

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🌟 Credits

Inspired by [Go's singleflight pattern](https://pkg.go.dev/golang.org/x/sync/singleflight) and adapted for Python's async/await paradigm.

## 🤔 FAQ

**Q: What happens if the leader fails?**  
A: All waiting callers receive the same exception. They can retry, which will elect a new leader.

**Q: How is this different from caching?**  
A: Caching stores past results. Coalescing deduplicates *in-flight* requests. They complement each other.

**Q: Does this work with FastAPI/Django/Flask?**  
A: Yes! It's framework-agnostic. Just decorate your data-fetching functions.

**Q: What about memory leaks?**  
A: Completed calls are automatically cleaned up. Use `forget()` or `forget_all()` for manual control.

---

**Built with ❤️ to make Python applications faster and more resilient.**
