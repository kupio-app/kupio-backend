from uuid import UUID

from sqlalchemy import select

from src.core.database.base_repository import BaseRepository
from src.domains.images.models import Image, ListingImage


class ImagesRepository(BaseRepository):
    async def get_by_id(self, image_id: UUID) -> Image | None:
        return await self._get(Image, Image.id == image_id)

    async def create(self, s3_key: str, content_type: str, size_bytes: int) -> Image:
        return await self._add(
            Image, s3_key=s3_key, content_type=content_type, size_bytes=size_bytes
        )

    async def delete(self, image_id: UUID):
        return await self._soft_delete(Image, Image.id == image_id)


class ListingImagesRepository(BaseRepository):
    async def get_by_listing(self, listing_id: UUID) -> list[ListingImage]:
        return await self._get_many(
            ListingImage,
            ListingImage.listing_id == listing_id,
            order_by=(ListingImage.sort_order.asc(),),
        )

    async def get_images_for_listing(
        self, listing_id: UUID
    ) -> list[tuple[ListingImage, Image]]:
        stmt = (
            select(ListingImage, Image)
            .join(Image, Image.id == ListingImage.image_id)
            .where(ListingImage.listing_id == listing_id)
            .order_by(ListingImage.sort_order.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.all())

    async def get_images_for_listings(
        self, listing_ids: list[UUID]
    ) -> list[tuple[ListingImage, Image]]:
        if not listing_ids:
            return []

        stmt = (
            select(ListingImage, Image)
            .join(Image, Image.id == ListingImage.image_id)
            .where(ListingImage.listing_id.in_(listing_ids))
            .order_by(ListingImage.listing_id.asc(), ListingImage.sort_order.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.all())

    async def get_by_listing_and_image(
        self, listing_id, image_id
    ) -> ListingImage | None:
        return await self._get(
            ListingImage,
            ListingImage.listing_id == listing_id,
            ListingImage.image_id == image_id,
        )

    async def create(self, listing_id: UUID, image_id: UUID, sort_order: int):
        return await self._add(
            ListingImage,
            listing_id=listing_id,
            image_id=image_id,
            sort_order=sort_order,
        )

    async def update_order(self, listing_image_id: UUID, sort_order: int):
        return await self._update(
            ListingImage,
            conditions=[ListingImage.id == listing_image_id],
            load_result=False,
            sort_order=sort_order,
        )

    async def delete(self, id: UUID) -> bool:
        return await self._delete(ListingImage, ListingImage.id == id)
