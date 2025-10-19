# shared-call-py Documentation

Complete technical documentation for request coalescing in Python.

## Overview

**shared-call-py** provides request coalescing (deduplication) for Python applications. When multiple concurrent requests ask for the same resource, only one execution happens—all others wait and share the result.

### Available Implementations

- **`AsyncSharedCall`**: Async/await implementation using `asyncio` (recommended)
- **`SharedCall`**: Synchronous implementation using `threading`

Both provide identical APIs: `group()` decorator, `call()` method, statistics tracking, and cache invalidation.

## Quick Links

- [Quick Start Guide](./quickstart.md) - Get started in 5 minutes
- [API Reference](./api-reference.md) - Complete API documentation
- [Benchmarks](./benchmarks/) - Performance results and comparisons
- [Examples](../examples/) - Real-world usage patterns

## Key Concepts

### Leader Election
The first caller for a key becomes the "leader" and performs the actual work. All concurrent callers for the same key wait for the leader's result.

### Automatic Key Generation
Keys are automatically generated from:
- Function module name
- Function name  
- Hashed arguments and keyword arguments

This means `fetch_user(42)` and `fetch_user(42)` will coalesce, but `fetch_user(42)` and `fetch_user(43)` will not.

### Custom Key Functions
Override automatic key generation for fine-grained control:

```python
@shared.group(key_fn=lambda user_id, timestamp: f"user:{user_id}")
async def fetch_user(user_id: int, timestamp: float):
    # Coalesces by user_id only, ignores timestamp
    return await db.get_user(user_id)
```

### Statistics Tracking
Monitor coalescing efficiency:
- **Hits**: Requests that were coalesced
- **Misses**: Requests that executed
- **Errors**: Requests that failed  
- **Active**: Currently in-flight calls
- **Hit Rate**: Coalescing efficiency percentage

### Cache Invalidation
Remove keys from tracking:
- `forget(key)`: Remove specific key
- `forget_all()`: Clear all tracked calls

## Usage Examples

### Asynchronous (Recommended)

```python
import asyncio
from shared_call_py import AsyncSharedCall

shared = AsyncSharedCall()

@shared.group()
async def fetch_user(user_id: int):
    """Expensive database query"""
    print(f"🔍 Fetching user {user_id}...")
    return await db.query("SELECT * FROM users WHERE id = ?", user_id)

# 100 concurrent requests = 1 database query
async def main():
    tasks = [fetch_user(42) for _ in range(100)]
    results = await asyncio.gather(*tasks)
    print(f"✅ {len(results)} results, only 1 DB query!")

asyncio.run(main())
```

### Synchronous

```python
from shared_call_py import SharedCall
import threading

shared = SharedCall()

@shared.group()
def expensive_computation(x: int):
    """CPU-intensive operation"""
    import time
    time.sleep(1)
    return x * 2

# Multiple threads calling simultaneously
result = expensive_computation(5)
```

## Error Propagation

When the leader execution fails, all waiting callers receive the same exception:

```python
@shared.group()
async def may_fail():
    raise ValueError("Database connection failed")

# All 10 requests receive the same ValueError
tasks = [may_fail() for _ in range(10)]
try:
    await asyncio.gather(*tasks)
except ValueError as e:
    print(f"All requests failed: {e}")
```

## Monitoring

### Get Statistics

```python
stats = await shared.get_stats()

print(f"Coalescing Rate: {stats.hit_rate:.1%}")
print(f"Requests Coalesced: {stats.hits}")
print(f"Actual Executions: {stats.misses}")
print(f"In-Flight Calls: {stats.active}")
print(f"Errors: {stats.errors}")
```

### Reset Statistics

```python
await shared.reset_stats()
```

## Cache Management

### Forget Specific Key

```python
# Remove user:42 from tracking
await shared.forget("user:42")
```

### Clear All Keys

```python
# Clear all in-flight call tracking
await shared.forget_all()
```

## Use Cases

### 1. Database Load Protection
Prevent connection pool exhaustion:
```python
@shared.group()
async def get_popular_product(product_id: int):
    return await db.query("SELECT * FROM products WHERE id = ?", product_id)
```

### 2. Cache Stampede Prevention
Protect against thundering herd:
```python
@shared.group()
async def get_config():
    if not cache.exists("config"):
        config = await load_from_db()
        cache.set("config", config, ttl=3600)
        return config
    return cache.get("config")
```

### 3. Rate Limit Protection
Stay within API quotas:
```python
@shared.group()
async def fetch_from_external_api(endpoint: str):
    return await external_api.get(endpoint)
```

### 4. Webhook Deduplication
Process duplicate webhooks once:
```python
@shared.group(key_fn=lambda webhook_id, data: webhook_id)
async def process_webhook(webhook_id: str, data: dict):
    return await payment_processor.handle(webhook_id)
```

## Thread Safety

- **AsyncSharedCall**: Safe for concurrent async tasks within a single event loop
- **SharedCall**: Safe for multi-threaded applications

## Performance Characteristics

- **Memory**: O(n) where n = number of unique in-flight keys
- **Overhead**: ~1-2ms per coalesced request (event synchronization)
- **Cleanup**: Automatic when execution completes
- **Scalability**: Tested with 1000+ concurrent requests

## Best Practices

### ✅ DO

- Coalesce read operations (GET, SELECT)
- Use for expensive operations with identical inputs
- Monitor statistics in production
- Use custom `key_fn` for fine-grained control
- Handle errors appropriately

### ❌ DON'T

- Coalesce write operations (POST, PUT, DELETE)
- Coalesce user-specific authenticated requests
- Rely on side effects (only return values are shared)
- Forget to handle exceptions
- Use sync version for async code

## Real-World Impact

### Database Load: **92.6x faster**
100 concurrent database requests reduced from 6.012s to 0.065s

### Cache Stampede: **99% query reduction**  
100 requests during cache expiration = 1 database query

### Rate Limits: **0% failures**
100 concurrent API requests = 1 API call, zero rate limit violations

[See detailed benchmarks →](./benchmarks/)

## Architecture

```
Request 1 (Leader) ──→ [Execute Function] ──→ Result
Request 2 (Waiter) ──→ [Wait for Leader] ───→ Result
Request 3 (Waiter) ──→ [Wait for Leader] ───→ Result
Request N (Waiter) ──→ [Wait for Leader] ───→ Result
```

## Global Instances

Pre-created instances for convenience:

```python
from shared_call_py import shared, async_shared

# Use directly
@shared.group()
def sync_function():
    ...

@async_shared.group()
async def async_function():
    ...
```

Or create isolated instances:

```python
from shared_call_py import AsyncSharedCall

user_service = AsyncSharedCall()
order_service = AsyncSharedCall()
```

## Next Steps

- **New user?** Start with the [Quick Start Guide](./quickstart.md)
- **Need details?** Check the [API Reference](./api-reference.md)
- **Want proof?** See [Benchmarks](./benchmarks/)
- **Real examples?** Browse [Examples](../examples/)

---

**Inspired by [Go's singleflight](https://pkg.go.dev/golang.org/x/sync/singleflight), optimized for Python's async/await paradigm.**
