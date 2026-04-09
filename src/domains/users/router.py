from fastapi import APIRouter, Depends

from src.core.dependencies import get_current_user
from src.core.utils.pagination import PaginationParams
from src.domains.listings.dependencies import get_listings_service
from src.domains.listings.enums import ListingStatus
from src.domains.listings.schemas import ListListingsResponse
from src.domains.listings.service import ListingsService

from .dependencies import get_users_service, get_user_by_username
from .models import User
from .schemas import SetUsernameRequest, UpdateUserProfile, UserPrivate, UserPublic
from .service import UsersService

router = APIRouter()


@router.patch("/me/profile", response_model=UserPrivate)
async def update_profile(
    user_data: UpdateUserProfile,
    current_user: User = Depends(get_current_user),
    service: UsersService = Depends(get_users_service),
):
    user = await service.update_profile(current_user, user_data)
    return await service.to_user_private(user)


@router.patch("/me/username", response_model=UserPrivate)
async def set_username(
    payload: SetUsernameRequest,
    current_user: User = Depends(get_current_user),
    service: UsersService = Depends(get_users_service),
):
    user = await service.set_username(current_user, payload)
    return await service.to_user_private(user)


@router.get("/me", response_model=UserPrivate)
async def me(
    current_user: User = Depends(get_current_user),
    service: UsersService = Depends(get_users_service),
):
    return await service.to_user_private(current_user)


@router.get("/me/listings", response_model=ListListingsResponse)
async def get_my_listings(
    status: ListingStatus | None = None,
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_user),
    service: ListingsService = Depends(get_listings_service),
):
    return await service.list_listings(
        current_user.id, status=status, limit=pagination.limit, cursor=pagination.cursor
    )


@router.get("/{username}", response_model=UserPublic)
async def get_user(
    user: User = Depends(get_user_by_username),
    service: UsersService = Depends(get_users_service),
):
    return await service.to_user_public(user)


@router.get("/{username}/listings", response_model=ListListingsResponse)
async def get_user_listings(
    pagination: PaginationParams = Depends(),
    user: User = Depends(get_user_by_username),
    service: ListingsService = Depends(get_listings_service),
):
    return await service.list_listings(
        user.id,
        status=ListingStatus.ACTIVE,
        limit=pagination.limit,
        cursor=pagination.cursor,
    )
