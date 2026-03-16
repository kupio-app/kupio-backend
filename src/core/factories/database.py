from fastapi import FastAPI
from sqlalchemy import URL
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import AppConfig
from src.core.utils.mjson import database_json_serializer


def _create_db_pool(url: URL) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    engine: AsyncEngine = create_async_engine(
        url=url,
        pool_size=20,
        max_overflow=60,
        json_serializer=database_json_serializer,
    )

    session_factory = async_sessionmaker(
        engine, autocommit=False, autoflush=False, expire_on_commit=False
    )
    return engine, session_factory


def init_db(
    app: FastAPI, config: AppConfig
) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    engine, session_factory = _create_db_pool(config.postgres.build_url())
    app.state.db_engine = engine
    app.state.db_session_factory = session_factory

    return engine, session_factory


async def shutdown_db(app: FastAPI) -> None:
    await app.state.db_engine.dispose()
