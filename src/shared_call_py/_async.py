import asyncio
from collections.abc import Callable
from dataclasses import replace
from functools import wraps
from typing import Any, Optional, TypeVar

from shared_call_py._core import Result, Stats, generate_key


T = TypeVar("T")

class AsyncCall:
    """Internal container tracking the state of an in-flight async call."""

    def __init__(self, result: Result, event: asyncio.Event):
        """Store the placeholder `result` and completion `event` for the call."""
        self.result = result
        self.event = event


class AsyncSharedCall:
    """Deduplicate concurrent async requests to the same function with identical arguments.

    When multiple awaiters request the same operation simultaneously, only one actually
    executes while others wait for and share the result. This dramatically reduces load
    on databases, external APIs, and expensive computations.

    Example:
        >>> shared = AsyncSharedCall()
        >>> @shared.group()
        ... async def fetch_user(user_id: int):
        ...     return await expensive_db_query(user_id)
        >>>
        >>> # 100 concurrent calls = 1 database query
        >>> results = await asyncio.gather(*[fetch_user(42) for _ in range(100)])
    """

    def __init__(self):
        """Initialize a new async request coalescing coordinator."""
        self.in_flight: dict[str, AsyncCall] = {}
        self.forgotten: set[str] = set()
        self.lock = asyncio.Lock()
        self.stats = Stats()

    async def call(self, key: Optional[str], fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute an async function with automatic deduplication of concurrent identical calls.

        If another awaiter is already executing the same function with the same arguments,
        this awaiter will wait for and receive that result instead of executing again.

        Args:
            key: Optional cache key. If None, auto-generated from function and arguments.
            fn: The async function to execute.
            *args: Positional arguments to pass to fn.
            **kwargs: Keyword arguments to pass to fn.

        Returns:
            The result of await fn(*args, **kwargs).

        Raises:
            Any exception raised by fn is propagated to all waiting awaiters.
        """
        if not key:
            key = f"{fn.__module__}.{fn.__name__}:{generate_key(*args, **kwargs)}"

        async with self.lock:
            # Check if this key has been forgotten - if so, don't coalesce
            if key in self.forgotten:
                self.forgotten.discard(key)
                is_forgotten = True
            else:
                is_forgotten = False

            if not is_forgotten and key in self.in_flight:
                self.stats.hits += 1
                fn_call = self.in_flight[key]
                is_leader = False
            else:
                self.stats.misses += 1
                self.stats.in_flight += 1
                fn_call = AsyncCall(result=Result(), event=asyncio.Event())
                self.in_flight[key] = fn_call
                is_leader = True

        if is_leader:
            try:
                result = await fn(*args, **kwargs)
                fn_call.result = Result(value=result)
            except Exception as e:
                fn_call.result = Result(error=e)
                self.stats.errors += 1
            finally:
                async with self.lock:
                    self.in_flight.pop(key, None)
                    self.stats.in_flight -= 1
                fn_call.event.set()

        await fn_call.event.wait()
        return fn_call.result.unwrap()

    async def get_stats(self) -> Stats:
        """Get current coalescing statistics.

        Returns:
            Stats object with hits (coalesced calls), misses (actual executions),
            errors (failed executions), and in_flight (currently running).
        """
        async with self.lock:
            return replace(self.stats)

    async def reset_stats(self):
        """Reset all statistics counters to zero."""
        async with self.lock:
            self.stats = Stats()

    async def forget(self, key: str):
        """Stop coalescing future calls for this key.

        Marks the key as forgotten so the next call with this key will execute
        independently rather than waiting for any in-flight call. Useful when
        you know data has changed and cached results should not be reused.

        Args:
            key: The cache key to forget.

        Example:
            >>> await shared.forget("user:123")
            >>> # Next call for user:123 will execute, not coalesce
        """
        async with self.lock:
            self.forgotten.add(key)

    async def forget_all(self):
        """Stop coalescing for all keys.

        All future calls will execute independently until new in-flight calls are established.
        """
        async with self.lock:
            for key in self.in_flight:
                self.forgotten.add(key)

    def group(
        self, key_fn: Optional[Callable[..., str]] = None
    ) -> Callable[[Callable[..., T]], Callable[..., T]]:
        """Decorator that enables automatic async request deduplication.

        Wraps an async function so concurrent calls with identical arguments share a single execution.
        Perfect for expensive operations like database queries, API calls, or heavy computations.

        Args:
            key_fn: Optional function to generate cache key from arguments.
                   If not provided, key is auto-generated from all arguments.
                   Signature: key_fn(*args, **kwargs) -> str

        Returns:
            A decorator that wraps your async function with coalescing behavior.

        Example:
            >>> shared = AsyncSharedCall()
            >>>
            >>> @shared.group()
            ... async def fetch_user(user_id):
            ...     return await expensive_db_query(user_id)
            >>>
            >>> # Custom key for complex scenarios
            >>> @shared.group(key_fn=lambda uid, opts: f"user:{uid}:{opts['detail']}")
            ... async def fetch_user_with_options(user_id, options):
            ...     return await db.query_with_options(user_id, options)
        """

        def decorator(fn: Callable[..., T]) -> Callable[..., T]:
            """Wrap `fn` so that concurrent awaiters share a single execution."""

            @wraps(fn)
            async def wrapper(*args: Any, **kwargs: Any) -> T:
                """Execute `fn` via the shared call registry for the computed key."""
                # Generate key using key_fn if provided, otherwise let call() auto-generate
                custom_key = key_fn(*args, **kwargs) if key_fn else None
                return await self.call(custom_key, fn, *args, **kwargs)

            return wrapper
        return decorator
