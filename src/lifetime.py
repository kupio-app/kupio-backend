from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.core.config import get_config
from src.core.factories.database import init_db, shutdown_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = get_config()

    engine, session_pool = init_db(app, config)

    yield

    await shutdown_db(app)
