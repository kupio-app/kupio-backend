from fastapi import FastAPI
from redis.asyncio import Redis, ConnectionPool

from src.core.config import AppConfig


def _create_redis(url: str) -> Redis | None:
    """Create Redis client."""
    return Redis(connection_pool=ConnectionPool.from_url(url=url))


def init_redis(app: FastAPI, config: AppConfig) -> Redis | None:
    """
    Initialize Redis client and place it in application state for later use.

    :return: Redis client instance.
    """
    redis = _create_redis(config.redis.build_url())
    app.state.redis = redis
    return redis


async def shutdown_redis(app: FastAPI) -> None:
    """Shutdown Redis client."""
    await app.state.redis.shutdown()
