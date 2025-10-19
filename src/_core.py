import hashlib
import pickle
from dataclasses import dataclass
from typing import Optional, TypeVar


T = TypeVar("T")


@dataclass
class Result:
    value: Optional[T] = None
    error: Optional[Exception] = None

    def is_success(self) -> bool:
        return self.error is None

    def is_error(self) -> bool:
        return self.error is not None

    def unwrap(self) -> T:
        if self.is_error():
            raise self.error
        return self.value


@dataclass
class Stats:
    """Statistics for a SharedCall instance."""

    hits: int = 0  # Requests coalesced
    misses: int = 0  # Actual executions
    errors: int = 0  # Failed executions
    in_flight: int = 0  # Currently executing

    @property
    def hit_rate(self) -> float:
        """Calculate hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


def generate_key(*args, **kwargs) -> str:
    """Generate a cache key from function arguments."""
    try:
        key_data = (args, tuple(sorted(kwargs.items())))
        serialized = pickle.dumps(key_data)
        return hashlib.sha256(serialized).hexdigest()[:16]
    except (TypeError, pickle.PicklingError):
        return hashlib.sha256(repr((args, kwargs)).encode()).hexdigest()[:16]
