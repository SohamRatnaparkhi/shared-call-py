import threading
from collections.abc import Callable
from dataclasses import replace
from functools import wraps
from typing import Any, Optional, TypeVar

from src._core import Result, Stats, generate_key


T = TypeVar("T")

class SyncCall:
    """Internal container tracking the state of an in-flight synchronous call."""

    def __init__(self, result: Result, event: threading.Event):
        """Store the placeholder `result` and completion `event` for the call."""
        self.result = result
        self.event = event


class SharedCall:
    """Coordinate synchronous request coalescing across concurrent callers."""

    def __init__(self):
        """Initialise shared state for tracking in-flight calls and statistics."""
        self.in_flight: dict[str, SyncCall] = {}
        self.lock = threading.Lock()
        self.stats = Stats()

    def call(self, key: Optional[str], fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Invoke `fn`, ensuring only one caller performs work for the derived `key`."""
        if not key:
            key = f"{fn.__module__}.{fn.__name__}:{generate_key(*args, **kwargs)}"

        with self.lock:
            if key in self.in_flight:
                self.stats.hits += 1
                fn_call = self.in_flight[key]
                is_leader = False
            else:
                self.stats.misses += 1
                self.stats.in_flight += 1
                fn_call = SyncCall(result=Result(), event=threading.Event())
                self.in_flight[key] = fn_call
                is_leader = True

        if is_leader:
            try:
                fn_call.result = Result(value=fn(*args, **kwargs))
            except Exception as e:
                fn_call.result = Result(error=e)
                self.stats.errors += 1
            finally:
                with self.lock:
                    self.in_flight.pop(key, None)
                    self.stats.in_flight -= 1
                fn_call.event.set()

        fn_call.event.wait()
        return fn_call.result.unwrap()

    def get_stats(self) -> Stats:
        """Return a snapshot of accumulated `Stats` without mutating internal state."""
        with self.lock:
            return replace(self.stats)

    def reset_stats(self):
        """Reset all tracked metrics to their initial values."""
        with self.lock:
            self.stats = Stats()

    def forget(self, key: str):
        """Drop any cached in-flight call associated with `key`."""
        with self.lock:
            self.in_flight.pop(key, None)

    def forget_all(self):
        """Clear every tracked in-flight call."""
        with self.lock:
            self.in_flight.clear()

    def group(
        self, key_fn: Optional[Callable[..., str]] = None
    ) -> Callable[[Callable[..., T]], Callable[..., T]]:
        """Decorator for automatic request coalescing.

        Args:
            key_fn: Optional function to generate key from arguments.
                    Signature: key_fn(*args, **kwargs) -> str

        Usage:
            shared = SharedCall()

            @shared.group()
            def get_user(user_id):
                return db.query(user_id)

            @shared.group(key_fn=lambda user_id: f"user:{user_id}")
            def get_user_detailed(user_id, include_posts=False):
                return db.query_with_options(user_id, include_posts)
        """
        def decorator(fn: Callable[..., T]) -> Callable[..., T]:
            """Wrap `fn` so that concurrent callers share a single execution."""

            @wraps(fn)
            def wrapper(*args: Any, **kwargs: Any) -> T:
                """Execute `fn` via the shared call registry for the computed key."""
                custom_key = key_fn(*args, **kwargs) if key_fn else None
                return self.call(custom_key, fn, *args, **kwargs)

            return wrapper

        return decorator
