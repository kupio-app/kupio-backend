from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.core.config import get_config
from src.core.factories.database import init_db, shutdown_db
from src.core.factories.redis import init_redis, shutdown_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = get_config()

    engine, session_pool = init_db(app, config)
    redis = init_redis(app, config)

    try:
        yield
    finally:
        await shutdown_db(app)
        await shutdown_redis(app)
