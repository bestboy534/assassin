from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession


@asynccontextmanager
async def transaction(session: AsyncSession) -> AsyncIterator[AsyncSession]:
    if session.in_transaction():
        async with session.begin_nested():
            yield session
        return

    async with session.begin():
        yield session
