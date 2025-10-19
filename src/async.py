import asyncio  # noqa: N999
from collections.abc import Callable
from dataclasses import replace
from functools import wraps
from typing import Any, Optional, TypeVar

from src._core import Result, Stats, generate_key


T = TypeVar("T")

class AsyncCall:
    def __init__(self, result: Result, event: asyncio.Event):
        self.result = result
        self.event = event

class AsyncSharedCall:
    def __init__(self):
        self.in_flight: dict[str, AsyncCall] = {}
        self.lock = asyncio.Lock()
        self.stats = Stats()

    async def call(self, key: Optional[str], fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        if not key:
            key = f"{fn.__module__}.{fn.__name__}:{generate_key(*args, **kwargs)}"

        async with self.lock:
            if key in self.in_flight:
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
        async with self.lock:
            return replace(self.stats)

    async def reset_stats(self):
        async with self.lock:
            self.stats = Stats()

    async def forget(self, key: str):
        async with self.lock:
            self.in_flight.pop(key, None)

    async def forget_all(self):
        async with self.lock:
            self.in_flight.clear()

    def group(
        self, key_fn: Optional[Callable[..., str]] = None
    ) -> Callable[[Callable[..., T]], Callable[..., T]]:
        """Decorator for automatic request coalescing.

        Args:
            key_fn: Optional function to generate key from arguments.
                    Signature: key_fn(*args, **kwargs) -> str

        Usage:
            shared = AsyncSharedCall()

            @shared.group()
            async def get_user(user_id):
                return await db.query(user_id)

            @shared.group(key_fn=lambda user_id: f"user:{user_id}")
            async def get_user_detailed(user_id, include_posts=False):
                return await db.query_with_options(user_id, include_posts)
        """
        def decorator(fn: Callable[..., T]) -> Callable[..., T]:
            @wraps(fn)
            async def wrapper(*args: Any, **kwargs: Any) -> T:
                # Generate key using key_fn if provided, otherwise let call() auto-generate
                custom_key = key_fn(*args, **kwargs) if key_fn else None
                return await self.call(custom_key, fn, *args, **kwargs)
            return wrapper
        return decorator
