from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import lru_cache
from pathlib import Path

from sqlalchemy import MetaData, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool

from .config import Settings, get_settings

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class Database:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        url = make_url(settings.database_url)
        if (
            url.drivername.startswith("sqlite")
            and url.database is not None
            and url.database != ":memory:"
        ):
            Path(url.database).parent.mkdir(parents=True, exist_ok=True)
        engine_options: dict[str, object] = {
            "echo": settings.database_echo,
            "pool_pre_ping": True,
        }
        if settings.database_url.startswith("sqlite"):
            if ":memory:" in settings.database_url:
                engine_options["poolclass"] = StaticPool
            engine_options["connect_args"] = {"check_same_thread": False}
        else:
            engine_options["pool_size"] = settings.database_pool_size
            engine_options["max_overflow"] = settings.database_max_overflow

        self.engine: AsyncEngine = create_async_engine(settings.database_url, **engine_options)
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def create_schema(self) -> None:
        import app.models  # noqa: F401

        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def drop_schema(self) -> None:
        import app.models  # noqa: F401

        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)

    async def ping(self) -> bool:
        try:
            async with self.engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
        except Exception:
            return False
        return True

    async def dispose(self) -> None:
        await self.engine.dispose()


@lru_cache(maxsize=8)
def database_for_url(database_url: str) -> Database:
    settings = get_settings().model_copy(update={"database_url": database_url})
    return Database(settings)


def get_database() -> Database:
    settings = get_settings()
    return database_for_url(settings.database_url)


async def get_session() -> AsyncIterator[AsyncSession]:
    settings = get_settings()
    if not settings.enable_database:
        raise RuntimeError("Database is disabled")
    database = get_database()
    async with database.session_factory() as session:
        yield session


@asynccontextmanager
async def session_scope(database: Database | None = None) -> AsyncIterator[AsyncSession]:
    target = database or get_database()
    async with target.session_factory() as session:
        yield session
