import threading
from collections.abc import Callable
from dataclasses import replace
from functools import wraps
from typing import Any, Optional, TypeVar

from src._core import Result, Stats, generate_key


T = TypeVar("T")

class SyncCall:
    def __init__(self, result: Result, event: threading.Event):
        self.result = result
        self.event = event

class SharedCall:
    def __init__(self):
        self.in_flight: dict[str, SyncCall] = {}
        self.lock = threading.Lock()
        self.stats = Stats()

    def call(self, key: Optional[str], fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
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
        with self.lock:
            return replace(self.stats)

    def reset_stats(self):
        with self.lock:
            self.stats = Stats()

    def forget(self, key: str):
        with self.lock:
            self.in_flight.pop(key, None)

    def forget_all(self):
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
            @wraps(fn)
            def wrapper(*args: Any, **kwargs: Any) -> T:
                custom_key = key_fn(*args, **kwargs) if key_fn else None
                return self.call(custom_key, fn, *args, **kwargs)
            return wrapper
        return decorator

