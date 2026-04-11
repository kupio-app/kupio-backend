from fastapi import Depends

from src.core.dependencies import RepositoriesDeps, get_uow
from src.core.database.uow import UoW

from .models import User
from .service import UsersService, DeviceTokenService


def get_users_service(
    repos: RepositoriesDeps,
    uow: UoW = Depends(get_uow),
) -> UsersService:
    return UsersService(repos=repos, uow=uow)


def get_device_token_service(
    repos: RepositoriesDeps,
    uow: UoW = Depends(get_uow),
) -> DeviceTokenService:
    return DeviceTokenService(repos=repos, uow=uow)


async def get_user_by_username(
    username: str,
    service: UsersService = Depends(get_users_service),
) -> User:
    return await service.get_user(username)
