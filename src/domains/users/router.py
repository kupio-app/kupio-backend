from fastapi import APIRouter, Depends

from src.core.database.uow import UoW
from src.core.dependencies import get_uow, RepositoriesDeps, get_current_user

from .schemas import UserPublic, UserPrivate, UpdateUserProfile
from .service import UsersService

router = APIRouter()


def get_users_service(
    repos: RepositoriesDeps,
    uow: UoW = Depends(get_uow),
) -> UsersService:
    return UsersService(repos=repos, uow=uow)


@router.patch("/me/profile", response_model=UserPrivate)
async def update_profile(
    user_data: UpdateUserProfile,
    current_user: UserPrivate = Depends(get_current_user),
    service: UsersService = Depends(get_users_service),
):
    return await service.update_profile(current_user, user_data)


@router.get("/{username}", response_model=UserPublic)
async def get_user(username: str, service: UsersService = Depends(get_users_service)):
    return await service.get_user(username)
