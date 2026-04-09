from fastapi import APIRouter, Depends, status

from src.core.dependencies import get_current_user
from src.domains.listings.dependencies import get_owned_listing_by_id
from src.domains.listings.models import Listing
from src.domains.users.models import User

from src.domains.promotions.dependencies import get_promotions_service
from src.domains.promotions.schemas import (
    ListingPromotionResponse,
    PurchasePromotionRequest,
)
from src.domains.promotions.service import PromotionsService

router = APIRouter()


@router.post(
    "/{listing_id}",
    response_model=ListingPromotionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def purchase_promotion(
    body: PurchasePromotionRequest,
    listing: Listing = Depends(get_owned_listing_by_id),
    current_user: User = Depends(get_current_user),
    service: PromotionsService = Depends(get_promotions_service),
):
    return await service.purchase(current_user, listing, body.packet_id)


@router.get("/{listing_id}", response_model=list[ListingPromotionResponse])
async def list_listing_promotions(
    listing: Listing = Depends(get_owned_listing_by_id),
    service: PromotionsService = Depends(get_promotions_service),
):
    return await service.list_for_listing(listing)
