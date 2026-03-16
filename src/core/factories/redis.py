from fastapi import FastAPI
from redis.asyncio import Redis, ConnectionPool

from src.core.config import AppConfig


def _create_redis(url: str) -> Redis | None:
    return Redis(connection_pool=ConnectionPool.from_url(url=url))


def init_redis(app: FastAPI, config: AppConfig) -> Redis | None:
    redis = _create_redis(config.redis.build_url())
    app.state.redis = redis
    return redis


async def shutdown_redis(app: FastAPI) -> None:
    await app.state.redis.shutdown()
