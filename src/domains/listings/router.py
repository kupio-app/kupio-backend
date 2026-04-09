import json

from fastapi import APIRouter, Depends, Query

from src.core.dependencies import get_current_user
from src.core.exceptions import UnprocessableEntityError
from src.core.utils.pagination import PaginationParams
from src.domains.users.models import User

from .dependencies import (
    get_listing_by_id,
    get_listings_service,
    get_owned_listing_by_id,
)
from .enums import ListingStatus
from .models import Listing
from .schemas import (
    ListingRequest,
    ListingResponse,
    ListListingsResponse,
    ListingStatusUpdateRequest,
)
from .service import ListingsService

router = APIRouter()


@router.get("", response_model=ListListingsResponse)
async def get_listings(
    pagination: PaginationParams = Depends(),
    category_id: int | None = Query(default=None),
    filters: str | None = Query(
        default=None, description='JSON object, {"ram":"16 GB"}'
    ),
    service: ListingsService = Depends(get_listings_service),
):
    custom_filters: dict | None = None
    if filters is not None:
        try:
            custom_filters = json.loads(filters)
            if not isinstance(custom_filters, dict):
                raise ValueError
        except json.JSONDecodeError, ValueError:
            raise UnprocessableEntityError("filters must be a valid JSON object")

    return await service.list_listings(
        status=ListingStatus.ACTIVE,
        category_id=category_id,
        custom_filters=custom_filters,
        limit=pagination.limit,
        cursor=pagination.cursor,
    )


@router.get("/{listing_id}", response_model=ListingResponse)
async def get_listing(
    listing: Listing = Depends(get_listing_by_id),
    service: ListingsService = Depends(get_listings_service),
):
    return await service._to_listing_response(listing)


@router.post("", response_model=ListingResponse)
async def create_listing(
    listing_data: ListingRequest,
    current_user: User = Depends(get_current_user),
    service: ListingsService = Depends(get_listings_service),
):
    listing = await service.create_listing(current_user, listing_data)
    return await service._to_listing_response(listing)


@router.put("/{listing_id}", response_model=ListingResponse)
async def update_listing(
    listing_data: ListingRequest,
    listing: Listing = Depends(get_owned_listing_by_id),
    service: ListingsService = Depends(get_listings_service),
):
    listing = await service.update_listing(listing, listing_data)
    return await service._to_listing_response(listing)


@router.put("/{listing_id}/status", response_model=ListingResponse)
async def update_listing_status(
    listing_data: ListingStatusUpdateRequest,
    listing: Listing = Depends(get_owned_listing_by_id),
    service: ListingsService = Depends(get_listings_service),
):
    listing = await service.update_listing_status(listing.id, listing_data.status)
    return await service._to_listing_response(listing)
