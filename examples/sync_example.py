from src._sync import SharedCall


shared = SharedCall()


@shared.group()
def load_user(user_id: str) -> dict[str, str]:
    return {"id": user_id, "name": f"User {user_id}"}


def main() -> None:
    result = load_user("42")
    print(f"Loaded user: {result}")


if __name__ == "__main__":
    main()
