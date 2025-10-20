# shared-call-py 🚀

**Eliminate redundant work and protect your systems from thundering herds with intelligent request coalescing.**

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Python implementation of request deduplication inspired by Go's [singleflight](https://pkg.go.dev/golang.org/x/sync/singleflight) pattern, improved with Python-first ergonomics. When multiple concurrent requests ask for the same resource, only one does the actual work—everyone else gets the same result instantly.

**No major code changes required.** Just use the `@shared.group()` decorator or simple functions like `call()` (execute once) and `forget()` (invalidate keys) as implemented in [`src/shared_call_py/_sync.py`](src/shared_call_py/_sync.py) and [`src/shared_call_py/_async.py`](src/shared_call_py/_async.py).

### ✨ Key Features

- 🚀 **92.6x faster** - Eliminate redundant database queries ([see benchmarks](#-benchmarks))
- 🔒 **Thread-safe & async-safe** - Works with `asyncio`, threads, and multiprocessing
- 🎯 **Zero dependencies** - Built on Python standard library only  
- 🧠 **Smart auto-keying** - Automatic deduplication based on function + arguments
- 📊 **Built-in monitoring** - Track hit rates, errors, and performance metrics
- 🏛️ **Production-ready** - Battle-tested patterns from high-scale systems

## 📋 Table of Contents

- [The Problem](#-the-problem)
- [Benchmarks](#-benchmarks)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Use Cases](#️-use-cases)
- [Advanced Features](#️-advanced-features)
- [Documentation](#-documentation)
- [How It Works](#-how-it-works)
- [When NOT to Use](#-when-not-to-use)
- [Development](#️-development)
- [FAQ](#-faq)

## 🎯 The Problem

Modern applications face three critical challenges:

1. **Thundering Herd**: When cache expires, hundreds of requests simultaneously hammer your database
2. **Rate Limit Hell**: Concurrent identical API calls burn through your rate limits
3. **Database Overload**: High concurrency creates connection pool exhaustion and query slowdowns

**Traditional approach**: Every request executes independently—wasting resources and destabilizing systems.

**shared-call-py approach**: Coalesce duplicate in-flight requests into a single execution. The first caller becomes the "leader" and does the work. All others wait and receive the same result.

## 📊 Benchmarks

Real-world performance improvements across different scenarios:

| Scenario | Without Coalescing | With Coalescing | Improvement |
|----------|-------------------|-----------------|-------------|
| **Database Load** | 6.01s, 100 queries | 0.07s, 1 query | **92.6x faster** |
| **Cache Stampede** | 100 DB hits | 1 DB hit | **99% reduction** |
| **Rate Limits** | 90% failed | 0% failed | **100% success** |
| **FastAPI Load Test** | 104s, 52s avg latency | 3.8s, 688ms avg latency | **27x faster** |

### FastAPI Example Load Test

The `examples/fastapi/` project includes load-testing scripts that highlight the impact of request coalescing in a real FastAPI application with a PostgreSQL database hosted on [Neon](https://neon.com/).

- **Normal endpoint** (`load_test_normal.sh`)

  - Total requests: 1000
  - Successful: 1000
  - Failed: 0
  - Total duration: 104.04s
  - Throughput: 9.61 req/s
  - Response times (ms): min 1057.45 · avg 52036.10 · max 102263 · p50 52118.40 · p95 97211.30 · p99 101256
- **Coalesced endpoint** (`load_test_coalesced.sh`)

  - Total requests: 1000
  - Successful: 1000
  - Failed: 0
  - Total duration: 3.84s
  - Throughput: 260.48 req/s
  - Response times (ms): min 52.71 · avg 688.04 · max 1462.63 · p50 731.44 · p95 1149.32 · p99 1432.18

Next, few other benchmark results and methodologies:

- [**Database Load Benchmark**](./docs/benchmarks/database-load.md) - Connection pool exhaustion prevention
- [**Cache Stampede Benchmark**](./docs/benchmarks/cache-stampede.md) - Thundering herd protection
- [**Rate Limit Benchmark**](./docs/benchmarks/rate-limits.md) - API quota preservation

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

Run them yourself:

```bash
python examples/mock_db_query.py
python examples/thundering_herd.py
python examples/ratelimit.py
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

Get up and running in under 2 minutes. Choose async (recommended for modern apps) or sync (for legacy/threaded code).

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

See [Quick Start](#-quick-start) for basic usage examples.

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

For basic usage, see [Quick Start](#-quick-start). These advanced features give you fine-grained control.

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

## 📚 Documentation

- [**Quick Start Guide**](./docs/quickstart.md) - Get started in 5 minutes
- [**API Reference**](./docs/api-reference.md) - Complete API documentation  
- [**Benchmarks**](./docs/benchmarks/) - Detailed performance comparisons ([also see above](#-benchmarks))
- [**Examples**](./examples/) - Real-world usage patterns including [FastAPI](./examples/fastapi/), [Django](./examples/django/), and [Flask](./examples/flask/)

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

❌ **Avoid coalescing in these scenarios:**

- **Mutations**: Don't coalesce write operations (POST, PUT, DELETE) - each must execute independently
- **User-specific data**: Each user needs their own result (unless you customize the [key function](#custom-key-functions))
- **Time-sensitive data**: When staleness matters (though you can use [`forget()`](#cache-invalidation) to invalidate keys)
- **Side effects**: Functions with important side effects beyond the return value

✅ **Perfect for:**
- Database queries ([example](#1-protect-your-database))
- External API calls ([rate limit protection](#2-respect-rate-limits))
- Cache warming ([stampede prevention](#3-prevent-cache-stampede))
- Expensive computations with identical inputs

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

Inspired by [Go&#39;s singleflight pattern](https://pkg.go.dev/golang.org/x/sync/singleflight) and adapted for Python's async/await paradigm.

## 🤔 FAQ

**Q: What happens if the leader fails?**  
A: All waiting callers receive the same exception. They can retry, which will elect a new leader.

**Q: How is this different from caching?**  
A: Caching stores *past* results. Coalescing deduplicates *in-flight* requests. They complement each other—use both for maximum efficiency!

**Q: Does this work with FastAPI/Django/Flask?**  
A: Yes! It's framework-agnostic. Check out our [examples](./examples/) for FastAPI, Django, and Flask integrations.

**Q: What about memory leaks?**  
A: Completed calls are automatically cleaned up. Use [`forget()`](#cache-invalidation) or `forget_all()` for manual control.

**Q: Can I use this with sync and async code?**  
A: Yes! Use `SharedCall` for sync/threaded code and `AsyncSharedCall` for async/await. See [Quick Start](#-quick-start).

**Q: How do I monitor performance?**  
A: Use [`get_stats()`](#statistics-and-monitoring) to track hit rates, misses, and errors. Perfect for observability dashboards!

---

**Built with ❤️ to make Python applications faster and more resilient.**
