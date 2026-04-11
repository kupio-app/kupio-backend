from fastapi import Depends
from redis.asyncio import Redis

from src.core.database.uow import UoW
from src.core.dependencies import RepositoriesDeps, get_uow, get_redis

from .redis import ChatRedisManager
from .service import ChatService, DeviceTokenService


def get_chat_redis(redis: Redis = Depends(get_redis)) -> ChatRedisManager:
    return ChatRedisManager(redis)


def get_chat_service(
    repos: RepositoriesDeps,
    uow: UoW = Depends(get_uow),
    chat_redis: ChatRedisManager = Depends(get_chat_redis),
) -> ChatService:
    return ChatService(repos=repos, uow=uow, chat_redis=chat_redis)


def get_device_token_service(
    repos: RepositoriesDeps,
    uow: UoW = Depends(get_uow),
) -> DeviceTokenService:
    return DeviceTokenService(repos=repos, uow=uow)
