from fastapi import Depends
from redis.asyncio import Redis

from src.core.database.uow import UoW
from src.core.dependencies import RepositoriesDeps, get_uow, get_redis
from .service import ChatService, DeviceTokenService


def get_chat_service(
    repos: RepositoriesDeps,
    uow: UoW = Depends(get_uow),
    redis: Redis = Depends(get_redis),
) -> ChatService:
    return ChatService(repos=repos, uow=uow, redis=redis)


def get_device_token_service(
    repos: RepositoriesDeps,
    uow: UoW = Depends(get_uow),
) -> DeviceTokenService:
    return DeviceTokenService(repos=repos, uow=uow)
