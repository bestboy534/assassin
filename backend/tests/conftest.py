import os
from collections.abc import AsyncIterator
from pathlib import Path

import pytest_asyncio

os.environ.setdefault("APP_ENVIRONMENT", "test")
os.environ.setdefault("USE_LLM", "false")
os.environ.setdefault("ENABLE_DATABASE", "false")
os.environ.setdefault("LOG_LEVEL", "warning")
os.environ.setdefault("QUEUE_BACKEND", "memory")
os.environ.setdefault("STORAGE_BACKEND", "local")

from app.config import Settings
from app.core.database import Database


@pytest_asyncio.fixture
async def database(tmp_path: Path) -> AsyncIterator[Database]:
    settings = Settings(
        app_environment="test",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'test.db'}",
        auto_create_schema=True,
        enable_database=True,
    )
    database = Database(settings)
    await database.create_schema()
    try:
        yield database
    finally:
        await database.dispose()
