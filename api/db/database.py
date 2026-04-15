import ssl
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from config import settings

connect_args = {}

if settings.database_url.startswith("postgresql"):
    ssl_context = ssl.create_default_context()
    connect_args["ssl"] = ssl_context

engine = create_async_engine(
    settings.database_url,
    echo=False,
    connect_args=connect_args,
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    try:
        from db.models import SavedSearch  # noqa

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    except Exception as e:
        import logging

        logging.exception(f"DB init failed: {e}")
        # IMPORTANT: don't crash app
