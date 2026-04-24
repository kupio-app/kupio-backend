from uuid import UUID

from fastapi import Depends

from src.core.dependencies import RepositoriesDeps, get_uow
from src.core.database.uow import UoW

from .models import User
from .service import UsersService, NotificationTokenService


def get_users_service(
    repos: RepositoriesDeps,
    uow: UoW = Depends(get_uow),
) -> UsersService:
    return UsersService(repos=repos, uow=uow)


def get_notification_token_service(
    repos: RepositoriesDeps,
    uow: UoW = Depends(get_uow),
) -> NotificationTokenService:
    return NotificationTokenService(repos=repos, uow=uow)


async def get_user_by_username(
    username: str,
    service: UsersService = Depends(get_users_service),
) -> User:
    return await service.get_user(username)


async def get_user_by_id(
    user_id: UUID,
    service: UsersService = Depends(get_users_service),
) -> User:
    return await service.get_user_by_id(user_id)
