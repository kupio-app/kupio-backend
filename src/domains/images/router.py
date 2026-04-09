from fastapi import APIRouter, Depends, UploadFile, File
from starlette import status

from src.core.database.base_model import UUID
from src.core.dependencies import get_current_user
from src.domains.images.dependencies import get_images_service
from src.domains.images.schemas import (
    ListingImageResponse,
    UpdateListingImagesOrderRequest,
)
from src.domains.images.service import ImageService
from src.domains.listings.dependencies import get_owned_listing_by_id
from src.domains.listings.models import Listing
from src.domains.users.models import User
from src.domains.users.schemas import UserPrivate
from src.domains.users.dependencies import get_users_service
from src.domains.users.service import UsersService

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


@router.put(
    "/listings/{listing_id}/images/order", status_code=status.HTTP_204_NO_CONTENT
)
async def update_listing_images_order(
    payload: UpdateListingImagesOrderRequest,
    service: ImageService = Depends(get_images_service),
    listing: Listing = Depends(get_owned_listing_by_id),
):
    return await service.reorder_listing_images(listing.id, payload.image_ids)


@router.put("/users/me/avatar", response_model=UserPrivate)
async def set_avatar(
    file: UploadFile = File(...),
    service: ImageService = Depends(get_images_service),
    current_user: User = Depends(get_current_user),
    users_service: UsersService = Depends(get_users_service),
):
    user = await service.set_user_avatar(current_user, file)
    return await users_service.to_user_private(user)


@router.delete("/users/me/avatar", status_code=status.HTTP_204_NO_CONTENT)
async def delete_avatar(
    service: ImageService = Depends(get_images_service),
    current_user: User = Depends(get_current_user),
) -> None:
    await service.remove_user_avatar(current_user)
