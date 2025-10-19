from ._async import AsyncSharedCall
from ._sync import SharedCall


shared = SharedCall()
async_shared = AsyncSharedCall()

__all__ = ["AsyncSharedCall", "SharedCall", "async_shared", "shared"]
