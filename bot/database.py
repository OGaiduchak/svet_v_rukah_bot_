from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


engine = None
session_factory: async_sessionmaker[AsyncSession] | None = None


def init_db(database_url: str) -> None:
    global engine, session_factory
    engine = create_async_engine(database_url, echo=False, future=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    if session_factory is None:
        raise RuntimeError("Database is not initialized")
    async with session_factory() as session:
        yield session
