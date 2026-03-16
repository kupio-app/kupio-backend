from fastapi import APIRouter, Depends

from src.core.database.repositories import Repositories
from src.core.database.uow import UoW
from src.core.dependencies import get_repo, get_uow

from .schemas import UserPublic
from .service import UsersService

router = APIRouter()


def get_users_service(
    repos: Repositories = Depends(get_repo),
    uow: UoW = Depends(get_uow),
) -> UsersService:
    return UsersService(repos=repos, uow=uow)


@router.get("/{username}", response_model=UserPublic)
async def get_user(username: str, service: UsersService = Depends(get_users_service)):
    return await service.get_user(username)
