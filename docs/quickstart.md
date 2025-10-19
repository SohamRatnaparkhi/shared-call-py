# Quick Start Guide

Get started with shared-call-py in 5 minutes.

## Installation

```bash
pip install shared-call-py
```

## Your First Coalesced Call

### Async (Recommended)

```python
import asyncio
from shared_call_py import AsyncSharedCall

# Create instance
shared = AsyncSharedCall()

# Decorate expensive function
@shared.group()
async def fetch_user(user_id: int):
    print(f"📡 Fetching user {user_id}...")
    await asyncio.sleep(1)  # Simulate slow API/DB
    return {"id": user_id, "name": f"User {user_id}"}

# Test it
async def main():
    # Fire 10 concurrent requests
    tasks = [fetch_user(42) for _ in range(10)]
    results = await asyncio.gather(*tasks)
    
    print(f"✅ {len(results)} results received")
    print(f"🔍 Only 1 actual fetch performed!")
    
    # Check stats
    stats = await shared.get_stats()
    print(f"📊 Coalescing rate: {stats.hit_rate:.1%}")

asyncio.run(main())
```

**Output:**
```
📡 Fetching user 42...
✅ 10 results received
🔍 Only 1 actual fetch performed!
📊 Coalescing rate: 90.0%
```

### Sync

```python
from shared_call_py import SharedCall
import time

shared = SharedCall()

@shared.group()
def expensive_computation(x: int):
    print(f"💭 Computing {x}...")
    time.sleep(1)
    return x * 2

# Use it
result = expensive_computation(5)
print(f"Result: {result}")
```

## Real-World Example: API Client

```python
import asyncio
import aiohttp
from shared_call_py import AsyncSharedCall

class GitHubClient:
    def __init__(self):
        self.shared = AsyncSharedCall()
        self.session = None
    
    @property
    async def http(self):
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def get_user(self, username: str):
        """Fetch user - automatically coalesced"""
        @self.shared.group()
        async def _fetch(name: str):
            session = await self.http
            async with session.get(f"https://api.github.com/users/{name}") as resp:
                return await resp.json()
        
        return await _fetch(username)
    
    async def close(self):
        if self.session:
            await self.session.close()

# Usage
async def main():
    client = GitHubClient()
    
    # Multiple services request same user simultaneously
    tasks = [client.get_user("octocat") for _ in range(20)]
    results = await asyncio.gather(*tasks)
    
    print(f"✅ Got {len(results)} results")
    print(f"🌐 Made only 1 API request!")
    
    await client.close()

asyncio.run(main())
```

## Custom Keys

By default, keys are generated from function name + arguments. Customize this:

```python
from shared_call_py import AsyncSharedCall

shared = AsyncSharedCall()

# Coalesce only by user_id, ignore timestamp
@shared.group(key_fn=lambda user_id, timestamp: f"user:{user_id}")
async def fetch_with_timestamp(user_id: int, timestamp: float):
    return await db.get_user(user_id)

# These will coalesce together (same user_id)
await fetch_with_timestamp(42, 1234567890)
await fetch_with_timestamp(42, 9999999999)  # Different timestamp, same key
```

## Monitoring

```python
# Get statistics
stats = await shared.get_stats()
print(f"Hits: {stats.hits}")           # Coalesced requests
print(f"Misses: {stats.misses}")       # Actual executions
print(f"Hit Rate: {stats.hit_rate:.1%}")  # Efficiency
print(f"Active: {stats.active}")       # In-flight calls
print(f"Errors: {stats.errors}")       # Failed executions

# Reset stats
await shared.reset_stats()
```

## Cache Invalidation

```python
# Remove specific key from tracking
await shared.forget("user:42")

# Clear all in-flight tracking
await shared.forget_all()
```

## Error Handling

Errors are propagated to all waiting callers:

```python
@shared.group()
async def failing_function():
    raise ValueError("Something went wrong!")

# All 10 callers get the same error
tasks = [failing_function() for _ in range(10)]
try:
    await asyncio.gather(*tasks)
except ValueError as e:
    print(f"All requests failed with: {e}")
```

## Next Steps

- [API Reference](./api-reference.md) - Complete API documentation
- [Benchmarks](./benchmarks/) - Performance characteristics
- [Examples](../examples/) - More real-world patterns

## Common Patterns

### Database Query Protection
```python
@shared.group()
async def get_popular_products():
    return await db.execute("SELECT * FROM products WHERE featured = true")
```

### Cache Stampede Prevention
```python
@shared.group()
async def get_config():
    if not cache.exists("config"):
        config = await load_from_db()
        cache.set("config", config, ttl=3600)
        return config
    return cache.get("config")
```

### Rate-Limited API
```python
@shared.group()
async def call_rate_limited_api(endpoint: str):
    # Only first caller hits the API, rest wait
    return await external_api.get(endpoint)
```
