import asyncio

from shared_call_py import AsyncSharedCall


shared = AsyncSharedCall()


@shared.group()
async def load_user(user_id: str) -> dict[str, str]:
    await asyncio.sleep(0.01)
    return {"id": user_id, "name": f"Async User {user_id}"}


async def main() -> None:
    result = await load_user("42")
    print(f"Loaded user: {result}")


if __name__ == "__main__":
    asyncio.run(main())
