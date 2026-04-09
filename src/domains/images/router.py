from fastapi import APIRouter, Depends, UploadFile, File
from starlette import status

from src.core.database.base_model import UUID
from src.domains.images.dependencies import get_images_service
from src.domains.images.schemas import ListingImageResponse
from src.domains.images.service import ImageService
from src.domains.listings.dependencies import get_owned_listing_by_id
from src.domains.listings.models import Listing

router = APIRouter()


@router.post(
    "/listings/{listing_id}/images",
    status_code=status.HTTP_201_CREATED,
    response_model=list[ListingImageResponse],
)
async def upload_listing_images(
    files: list[UploadFile] = File(...),
    service: ImageService = Depends(get_images_service),
    listing: Listing = Depends(get_owned_listing_by_id),
):
    return await service.upload_listing_images(listing.id, files)


@router.delete(
    "/listings/{listing_id}/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_listing_image(
    image_id: UUID,
    service: ImageService = Depends(get_images_service),
    listing: Listing = Depends(get_owned_listing_by_id),
):
    return await service.delete_listing_image(listing.id, image_id)
