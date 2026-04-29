from uuid import UUID

from fastapi import APIRouter, Depends, status

from src.core.dependencies import get_current_user
from src.core.utils.pagination import PaginationParams
from src.domains.listings.schemas import ListListingsResponse
from src.domains.users.models import User
from src.domains.listings.models import Listing
from src.domains.listings.dependencies import get_listing_by_id

from .dependencies import get_favourites_service
from .schemas import FavouritedListingsIds
from .service import FavouritesService

router = APIRouter()


@router.get("", response_model=ListListingsResponse)
async def get_favourites(
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_user),
    service: FavouritesService = Depends(get_favourites_service),
):
    return await service.list_favourites(
        current_user,
        limit=pagination.limit,
        cursor=pagination.cursor,
    )


@router.get("/ids", response_model=FavouritedListingsIds)
async def get_all_favourites_ids(
    current_user: User = Depends(get_current_user),
    service: FavouritesService = Depends(get_favourites_service),
):
    return await service.get_all_favourites_ids(current_user)


@router.post("/{listing_id}", status_code=status.HTTP_201_CREATED)
async def add_favourite(
    listing: Listing = Depends(get_listing_by_id),
    current_user: User = Depends(get_current_user),
    service: FavouritesService = Depends(get_favourites_service),
) -> None:
    await service.add_favourite(current_user, listing)


@router.delete("/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_favourite(
    listing_id: UUID,
    current_user: User = Depends(get_current_user),
    service: FavouritesService = Depends(get_favourites_service),
) -> None:
    await service.remove_favourite(current_user, listing_id)
