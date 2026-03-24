from fastapi import APIRouter, Depends

from src.core.dependencies import get_current_user
from src.domains.users.models import User

from .dependencies import (
    get_listing_by_id,
    get_listings_service,
    get_owned_listing_by_id,
)
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
async def get_listings(service: ListingsService = Depends(get_listings_service)):
    return await service.list_all_active()


@router.get("/{listing_id}", response_model=ListingResponse)
async def get_listing(listing: Listing = Depends(get_listing_by_id)):
    return listing


@router.post("", response_model=ListingResponse)
async def create_listing(
    listing_data: ListingRequest,
    current_user: User = Depends(get_current_user),
    service: ListingsService = Depends(get_listings_service),
):
    return await service.create_listing(current_user, listing_data)


@router.put("/{listing_id}")
async def update_listing(
    listing_data: ListingRequest,
    listing: Listing = Depends(get_owned_listing_by_id),
    service: ListingsService = Depends(get_listings_service),
):
    return await service.update(listing.id, listing_data)


@router.put("/{listing_id}/status", response_model=ListingResponse)
async def update_listing_status(
    listing_data: ListingStatusUpdateRequest,
    listing: Listing = Depends(get_owned_listing_by_id),
    service: ListingsService = Depends(get_listings_service),
):
    return await service.update_listing_status(listing.id, listing_data.status)
