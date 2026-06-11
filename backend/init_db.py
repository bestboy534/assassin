import asyncio

from app.core.database import get_database


async def main() -> None:
    database = get_database()
    await database.create_schema()
    await database.dispose()
    print("Database schema initialized")


if __name__ == "__main__":
    asyncio.run(main())
