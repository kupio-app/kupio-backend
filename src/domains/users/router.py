from fastapi import APIRouter, Depends, status, Query

from src.core.dependencies import get_current_user
from src.core.utils.pagination import PaginationParams
from src.domains.listings.dependencies import get_listings_service
from src.domains.listings.enums import ListingStatus
from src.domains.listings.schemas import ListListingsResponse, ListOwnerListingsResponse
from src.domains.listings.service import ListingsService
from src.domains.promotions.dependencies import get_promotions_service
from src.domains.promotions.schemas import ListPromotionsResponse
from src.domains.promotions.service import PromotionsService

from .dependencies import (
    get_users_service,
    get_notification_token_service,
    get_user_by_username,
    get_user_by_id,
)
from .models import User
from .schemas import (
    NotificationTokenResponse,
    RegisterNotificationTokenRequest,
    SetUsernameRequest,
    UpdateUserProfile,
    UserListingStatsResponse,
    UserPrivate,
    UserPublic,
)
from .service import UsersService, NotificationTokenService

router = APIRouter()


@router.patch("/me/profile", response_model=UserPrivate)
async def update_profile(
    user_data: UpdateUserProfile,
    current_user: User = Depends(get_current_user),
    service: UsersService = Depends(get_users_service),
):
    return await service.update_profile(current_user, user_data)


@router.patch("/me/username", response_model=UserPrivate)
async def set_username(
    payload: SetUsernameRequest,
    current_user: User = Depends(get_current_user),
    service: UsersService = Depends(get_users_service),
):
    return await service.set_username(current_user, payload)


@router.get("/me", response_model=UserPrivate)
async def me(
    current_user: User = Depends(get_current_user),
    service: UsersService = Depends(get_users_service),
):
    return await service.get_current_user_for_response(current_user.id)


@router.get("/me/stats", response_model=UserListingStatsResponse)
async def get_my_stats(
    current_user: User = Depends(get_current_user),
    service: ListingsService = Depends(get_listings_service),
):
    return await service.get_owner_dashboard_stats(current_user.id)


@router.get("/me/promotions", response_model=ListPromotionsResponse)
async def get_my_promotions(
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_user),
    service: PromotionsService = Depends(get_promotions_service),
):
    return await service.list_my_promotions(
        current_user.id,
        limit=pagination.limit,
        cursor=pagination.cursor,
    )


@router.get("/me/listings", response_model=ListOwnerListingsResponse)
async def get_my_listings(
    listing_status: ListingStatus | None = Query(None, alias="status"),
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_user),
    service: ListingsService = Depends(get_listings_service),
):
    return await service.list_owned_listings(
        current_user.id,
        status=listing_status,
        limit=pagination.limit,
        cursor=pagination.cursor,
    )


@router.post(
    "/me/notification-tokens",
    response_model=NotificationTokenResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_notification_token(
    payload: RegisterNotificationTokenRequest,
    current_user: User = Depends(get_current_user),
    service: NotificationTokenService = Depends(get_notification_token_service),
):
    return await service.register_token(current_user, payload)


@router.get("/{username}", response_model=UserPublic)
async def get_user(user: User = Depends(get_user_by_username)):
    return user


@router.get("/{user_id}", response_model=UserPublic)
async def get_user_by_id(user: User = Depends(get_user_by_id)):
    return user


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
