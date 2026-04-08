from uuid import UUID

from src.core.database.base_repository import BaseRepository
from src.domains.images.models import Image, ListingImage


class ImagesRepository(BaseRepository):
    async def get_by_id(self, image_id: UUID) -> Image | None:
        return await self._get(Image, Image.id == image_id)

    async def create(self, s3_key: str, content_type: str, size_bytes: int):
        return await self._add(
            Image, s3_key=s3_key, content_type=content_type, size_bytes=size_bytes
        )


class ListingImagesRepository(BaseRepository):
    async def get_by_listing(self, listing_id: UUID) -> list[ListingImage]:
        return await self._get_many(
            ListingImage,
            ListingImage.listing_id == listing_id,
            order_by=(ListingImage.sort_order.asc(),),
        )

    async def create(self, listing_id: UUID, image_id: UUID, sort_order: int):
        return await self._add(
            ListingImage,
            listing_id=listing_id,
            image_id=image_id,
            sort_order=sort_order,
        )

    async def delete(self, id: UUID) -> bool:
        return await self._delete(ListingImage, ListingImage.id == id)
