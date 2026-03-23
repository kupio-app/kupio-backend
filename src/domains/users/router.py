from fastapi import APIRouter, Depends

from src.core.database.uow import UoW
from src.core.dependencies import get_uow, RepositoriesDeps

from .schemas import UserPublic
from .service import UsersService

router = APIRouter()


def get_users_service(
    repos: RepositoriesDeps,
    uow: UoW = Depends(get_uow),
) -> UsersService:
    return UsersService(repos=repos, uow=uow)


@router.get("/{username}", response_model=UserPublic)
async def get_user(username: str, service: UsersService = Depends(get_users_service)):
    return await service.get_user(username)
