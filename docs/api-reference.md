# API Reference

Complete reference for shared-call-py.

## AsyncSharedCall

Async/await implementation using `asyncio`.

### Constructor

```python
AsyncSharedCall()
```

Creates a new instance for coalescing async functions.

**Example:**
```python
from shared_call_py import AsyncSharedCall

shared = AsyncSharedCall()
```

### Methods

#### `group(key_fn=None)`

Decorator to enable request coalescing on an async function.

**Parameters:**
- `key_fn` (callable, optional): Custom key generation function. Receives the same arguments as the decorated function. Returns a string key. Default: generates key from function name and hashed arguments.

**Returns:** Decorator function

**Example:**
```python
@shared.group()
async def fetch_user(user_id: int):
    return await db.get_user(user_id)

# Custom key
@shared.group(key_fn=lambda x, y: f"{x}")
async def compute(x: int, y: int):
    return x + y
```

#### `call(key, fn, *args, **kwargs)`

Direct API for coalescing without decorator.

**Parameters:**
- `key` (str): Unique key for coalescing
- `fn` (callable): Async function to execute
- `*args`: Positional arguments for `fn`
- `**kwargs`: Keyword arguments for `fn`

**Returns:** Awaitable result

**Example:**
```python
result = await shared.call("user:42", fetch_from_db, user_id=42)
```

#### `get_stats()`

Get current statistics.

**Returns:** `Stats` object with:
- `hits` (int): Number of coalesced requests
- `misses` (int): Number of actual executions
- `errors` (int): Number of failed executions
- `active` (int): Current in-flight calls
- `hit_rate` (float): Coalescing efficiency (hits / total)

**Example:**
```python
stats = await shared.get_stats()
print(f"Efficiency: {stats.hit_rate:.1%}")
```

#### `reset_stats()`

Reset statistics to zero.

**Example:**
```python
await shared.reset_stats()
```

#### `forget(key)`

Remove a key from in-flight tracking.

**Parameters:**
- `key` (str): Key to forget

**Example:**
```python
await shared.forget("user:42")
```

#### `forget_all()`

Clear all in-flight tracking.

**Example:**
```python
await shared.forget_all()
```

---

## SharedCall

Synchronous implementation using `threading`.

### Constructor

```python
SharedCall()
```

Creates a new instance for coalescing sync functions.

**Example:**
```python
from shared_call_py import SharedCall

shared = SharedCall()
```

### Methods

API identical to `AsyncSharedCall` but for synchronous functions.

#### `group(key_fn=None)`

Decorator for sync functions.

**Example:**
```python
@shared.group()
def fetch_user(user_id: int):
    return db.get_user(user_id)
```

#### `call(key, fn, *args, **kwargs)`

Direct API for sync functions.

**Example:**
```python
result = shared.call("user:42", fetch_from_db, user_id=42)
```

#### `get_stats()`

Returns `Stats` object (same as async version).

#### `reset_stats()`

Resets statistics.

#### `forget(key)`

Removes key from tracking.

#### `forget_all()`

Clears all tracking.

---

## Stats

Statistics object returned by `get_stats()`.

### Attributes

```python
@dataclass
class Stats:
    hits: int          # Requests that were coalesced
    misses: int        # Requests that executed
    errors: int        # Requests that failed
    active: int        # Currently in-flight
    
    @property
    def hit_rate(self) -> float:
        """Coalescing efficiency: hits / (hits + misses)"""
```

**Example:**
```python
stats = await shared.get_stats()
print(f"Coalesced: {stats.hits}")
print(f"Executed: {stats.misses}")
print(f"Efficiency: {stats.hit_rate:.1%}")
print(f"In-flight: {stats.active}")
```

---

## Result

Internal result wrapper (not typically used directly).

### Attributes

```python
@dataclass
class Result:
    value: Any         # Returned value
    error: Exception   # Exception if failed
    
    def unwrap(self) -> Any:
        """Returns value or raises error"""
```

---

## Key Generation

### Default Key Function

By default, keys are generated as:
```
{module_name}:{function_name}:{hash(args, kwargs)}
```

### Custom Key Functions

Provide `key_fn` to `@group()` decorator:

```python
# Coalesce by first argument only
@shared.group(key_fn=lambda user_id, *args, **kwargs: f"user:{user_id}")
async def fetch_user(user_id: int, include_details: bool = False):
    ...

# Coalesce by multiple fields
@shared.group(key_fn=lambda org, repo: f"{org}/{repo}")
async def get_github_repo(org: str, repo: str):
    ...

# No coalescing (unique key every time)
@shared.group(key_fn=lambda: str(uuid.uuid4()))
async def no_coalesce():
    ...
```

---

## Thread Safety & Async Safety

### AsyncSharedCall
- ✅ Safe for concurrent async tasks
- ✅ Uses `asyncio.Lock` and `asyncio.Event`
- ❌ Not safe for multi-threaded use (use separate instances per thread)

### SharedCall
- ✅ Safe for multi-threaded use
- ✅ Uses `threading.Lock` and `threading.Event`
- ❌ Cannot be used with async functions

---

## Error Propagation

When the leader execution fails:
1. Exception is captured
2. All waiting callers receive the **same exception**
3. Statistics record an error
4. Key is removed from tracking

**Example:**
```python
@shared.group()
async def may_fail():
    raise ValueError("Failed!")

# All 10 requests get the same error
tasks = [may_fail() for _ in range(10)]
try:
    await asyncio.gather(*tasks)
except ValueError:
    print("All requests failed together")

stats = await shared.get_stats()
print(f"Errors: {stats.errors}")  # 1 (not 10!)
```

---

## Best Practices

### DO ✅

- Coalesce read operations (GET, SELECT)
- Use for expensive computations with same inputs
- Monitor with `get_stats()` in production
- Use custom `key_fn` for fine-grained control
- Handle errors appropriately

### DON'T ❌

- Coalesce write operations (POST, PUT, DELETE)
- Coalesce user-specific authenticated requests
- Rely on side effects (only return value is shared)
- Forget to clean up with `forget()` if needed
- Use sync version for async code (or vice versa)

---

## Performance Characteristics

- **Memory**: O(n) where n = number of unique in-flight keys
- **Time**: O(1) for lock acquisition, O(1) for stats
- **Overhead**: ~1-2ms per coalesced request (event wait time)
- **Cleanup**: Automatic when execution completes

---

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

Or create your own for better isolation:
```python
from shared_call_py import AsyncSharedCall

# Per-service instance
user_service_shared = AsyncSharedCall()
order_service_shared = AsyncSharedCall()
```
