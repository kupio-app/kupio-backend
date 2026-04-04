from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from src.core.config import get_config
from src.core.factories.database import _create_db_pool

# Register all models with SQLAlchemy mapper before any queries run
import src.domains.users.models  # noqa: F401
import src.domains.auth.models  # noqa: F401
import src.domains.listings.models  # noqa: F401
import src.domains.categories.models  # noqa: F401
import src.domains.filter_definitions.models  # noqa: F401
import src.domains.favourites.models  # noqa: F401
import src.domains.payments.models  # noqa: F401
import src.domains.promotions.models  # noqa: F401


@dataclass
class WorkerContext:
    session_factory: async_sessionmaker[AsyncSession]


@asynccontextmanager
async def lifespan() -> AsyncGenerator[WorkerContext, None]:
    config = get_config()
    engine, session_factory = _create_db_pool(config.postgres.build_url())
    try:
        yield WorkerContext(session_factory=session_factory)
    finally:
        await engine.dispose()
