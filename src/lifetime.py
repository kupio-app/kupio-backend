from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.core.config import get_config
from src.core.factories.database import init_db, shutdown_db
from src.core.factories.redis import init_redis, shutdown_redis
from src.core.factories.s3 import init_s3, shutdown_s3


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = get_config()

    engine, session_pool = init_db(app, config)
    redis = init_redis(app, config)
    s3 = init_s3(app, config)

    try:
        yield
    finally:
        await shutdown_db(app)
        await shutdown_redis(app)
        await shutdown_s3(app)
