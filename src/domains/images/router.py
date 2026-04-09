from fastapi import APIRouter, Depends, UploadFile, File

from src.domains.images.dependencies import get_images_service
from src.domains.images.schemas import ListingImageResponse
from src.domains.images.service import ImageService
from src.domains.listings.dependencies import get_owned_listing_by_id
from src.domains.listings.models import Listing

router = APIRouter()


@router.post("/listings/{listing_id}/images", response_model=list[ListingImageResponse])
async def upload_listing_images(
    files: list[UploadFile] = File(...),
    service: ImageService = Depends(get_images_service),
    listing: Listing = Depends(get_owned_listing_by_id),
):
    return await service.upload_listing_images(listing.id, files)
