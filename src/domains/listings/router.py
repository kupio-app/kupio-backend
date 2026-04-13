import json
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from src.core.dependencies import get_current_user, get_current_user_or_none
from src.core.exceptions import UnprocessableEntityError
from src.core.utils.pagination import PaginationParams
from src.domains.reports.dependencies import get_reports_service
from src.domains.reports.schemas import (
    CreateListingReportRequest,
    CreatedListingReportResponse,
)
from src.domains.reports.service import ReportsService
from src.domains.users.models import User

from .dependencies import (
    get_listing_by_id,
    get_listings_service,
    get_owned_listing_by_id,
)
from .enums import ListingStatus
from .exceptions import InvalidListingPriceRangeError
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
    q: str | None = Query(default=None),
    category_id: int | None = Query(default=None),
    min_price: int | None = Query(default=None, ge=0),
    max_price: int | None = Query(default=None, ge=0),
    is_free: bool | None = Query(default=None),
    is_tradable: bool | None = Query(default=None),
    filters: str | None = Query(
        default=None, description='JSON object, {"ram":"16 GB"}'
    ),
    service: ListingsService = Depends(get_listings_service),
):
    if min_price is not None and max_price is not None and min_price > max_price:
        raise InvalidListingPriceRangeError()

    q = (q.strip() or None) if q is not None else None

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
        q=q,
        category_id=category_id,
        min_price=min_price,
        max_price=max_price,
        is_free=is_free,
        is_tradable=is_tradable,
        custom_filters=custom_filters,
        limit=pagination.limit,
        cursor=pagination.cursor,
    )


@router.get("/{listing_id}", response_model=ListingResponse)
async def get_listing(
    listing_id: UUID,
    count_seen: bool = Query(default=False),
    current_user: User | None = Depends(get_current_user_or_none),
    service: ListingsService = Depends(get_listings_service),
):
    return await service.get_listing_for_response(
        listing_id,
        current_user=current_user,
        count_seen=count_seen,
    )


@router.post("", response_model=ListingResponse)
async def create_listing(
    listing_data: ListingRequest,
    current_user: User = Depends(get_current_user),
    service: ListingsService = Depends(get_listings_service),
):
    return await service.create_listing(current_user, listing_data)


@router.put("/{listing_id}", response_model=ListingResponse)
async def update_listing(
    listing_data: ListingRequest,
    listing: Listing = Depends(get_owned_listing_by_id),
    service: ListingsService = Depends(get_listings_service),
):
    return await service.update_listing(listing, listing_data)


@router.put("/{listing_id}/status", response_model=ListingResponse)
async def update_listing_status(
    listing_data: ListingStatusUpdateRequest,
    listing: Listing = Depends(get_owned_listing_by_id),
    service: ListingsService = Depends(get_listings_service),
):
    return await service.update_listing_status(listing.id, listing_data.status)


@router.post(
    "/{listing_id}/reports",
    response_model=CreatedListingReportResponse,
    status_code=201,
)
async def create_listing_report(
    report_data: CreateListingReportRequest,
    listing: Listing = Depends(get_listing_by_id),
    current_user: User = Depends(get_current_user),
    service: ReportsService = Depends(get_reports_service),
):
    return await service.create_report(current_user, listing, report_data)
