from fastapi import Depends

from src.core.dependencies import RepositoriesDeps, get_uow
from src.core.database.uow import UoW
from src.core.dependencies import get_s3_storage_service
from src.core.storage.s3 import S3StorageService

from .models import User
from .service import UsersService


def get_users_service(
    repos: RepositoriesDeps,
    uow: UoW = Depends(get_uow),
    storage: S3StorageService = Depends(get_s3_storage_service),
) -> UsersService:
    return UsersService(repos=repos, uow=uow, storage=storage)


async def get_user_by_username(
    username: str,
    service: UsersService = Depends(get_users_service),
) -> User:
    return await service.get_user(username)
