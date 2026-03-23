from fastapi import APIRouter, Depends

from src.core.dependencies import get_current_user

from .dependencies import get_users_service, get_user_by_username
from .models import User
from .schemas import UserPublic, UserPrivate, UpdateUserProfile
from .service import UsersService

router = APIRouter()


@router.patch("/me/profile", response_model=UserPrivate)
async def update_profile(
    user_data: UpdateUserProfile,
    current_user: User = Depends(get_current_user),
    service: UsersService = Depends(get_users_service),
):
    return await service.update_profile(current_user, user_data)


@router.get("/{username}", response_model=UserPublic)
async def get_user(user: UserPublic = Depends(get_user_by_username)):
    return user
