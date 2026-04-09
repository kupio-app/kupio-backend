import io
import uuid

from fastapi import UploadFile
from starlette.concurrency import run_in_threadpool

from src.core.database.base_model import UUID
from src.core.database.repositories import Repositories
from src.core.database.uow import UoW
from src.core.storage.s3 import S3StorageService
from src.domains.images.consts import (
    MAX_IMAGE_SIZE_BYTES,
    ALLOWED_CONTENT_TYPES,
    CONTENT_TYPE_TO_EXTENSION,
)
from src.domains.images.exceptions import (
    ImageMaxSizeError,
    ImageContentTypeError,
    ListingImageNotFoundError,
    InvalidListingImageOrderError,
    UserAvatarNotFoundError,
)
from src.domains.images.schemas import ImageResponse
from src.domains.users.models import User


class ImageService:
    def __init__(self, repos: Repositories, uow: UoW, storage: S3StorageService):
        self.repos = repos
        self.image_repo = repos.images
        self.listing_images_repo = repos.listing_images
        self.user_repo = repos.users
        self.uow = uow
        self.storage = storage

    async def upload_listing_images(
        self,
        listing_id: UUID,
        files: list[UploadFile],
    ) -> list[ImageResponse]:
        prepared_files = []

        for file in files:
            content = await file.read()
            size_bytes = len(content)

            if size_bytes > MAX_IMAGE_SIZE_BYTES:
                raise ImageMaxSizeError()

            if file.content_type not in ALLOWED_CONTENT_TYPES:
                raise ImageContentTypeError()

            prepared_files.append(
                {
                    "content": content,
                    "size_bytes": size_bytes,
                    "content_type": file.content_type,
                }
            )

        existing_images = await self.listing_images_repo.get_by_listing(listing_id)
        next_sort_order = len(existing_images)

        uploaded_keys: list[str] = []
        responses: list[ImageResponse] = []

        try:
            async with self.uow:
                for prepared in prepared_files:
                    sort_order = next_sort_order
                    s3_key = build_listing_image_key(
                        listing_id, prepared["content_type"]
                    )

                    await run_in_threadpool(
                        self.storage.upload_file,
                        io.BytesIO(prepared["content"]),
                        s3_key,
                        prepared["content_type"],
                    )
                    uploaded_keys.append(s3_key)

                    image = await self.image_repo.create(
                        s3_key=s3_key,
                        content_type=prepared["content_type"],
                        size_bytes=prepared["size_bytes"],
                    )

                    await self.listing_images_repo.create(
                        listing_id=listing_id,
                        image_id=image.id,
                        sort_order=sort_order,
                    )

                    responses.append(
                        ImageResponse(
                            id=image.id,
                            url=self.storage.build_public_url(s3_key),
                            sort_order=sort_order,
                        )
                    )

                    next_sort_order += 1

        except Exception:
            for key in uploaded_keys:
                try:
                    await run_in_threadpool(self.storage.delete_object, key)
                except Exception:
                    pass
            raise

        return responses

    async def delete_listing_images(self, listing_id: UUID, image_ids: list[UUID]):
        async with self.uow:
            for image_id in image_ids:
                image_listing = await self.listing_images_repo.get_by_listing_and_image(
                    listing_id, image_id
                )
                if image_listing is None:
                    raise ListingImageNotFoundError()

                await self.listing_images_repo.delete(image_listing.id)
                await self.image_repo.delete(image_id)

    async def reorder_listing_images(self, listing_id: UUID, image_ids: list[UUID]):
        listing_images = await self.listing_images_repo.get_by_listing(listing_id)
        listing_images_ids = {li.image_id for li in listing_images}

        if listing_images_ids != set(image_ids):
            raise InvalidListingImageOrderError()

        async with self.uow:
            for listing_image in listing_images:
                await self.listing_images_repo.update_order(
                    listing_image.id, image_ids.index(listing_image.image_id)
                )

    async def set_user_avatar(self, user: User, file: UploadFile) -> User:
        content = await file.read()
        size_bytes = len(content)

        if size_bytes > MAX_IMAGE_SIZE_BYTES:
            raise ImageMaxSizeError()

        if file.content_type not in ALLOWED_CONTENT_TYPES:
            raise ImageContentTypeError()

        old_avatar_image_id = user.avatar_image_id
        s3_key = build_avatar_key(user.id, file.content_type)

        try:
            await run_in_threadpool(
                self.storage.upload_file,
                io.BytesIO(content),
                s3_key,
                file.content_type,
            )

            async with self.uow:
                image = await self.image_repo.create(
                    s3_key=s3_key,
                    content_type=file.content_type,
                    size_bytes=size_bytes,
                )

                user = await self.user_repo.update(
                    user_id=user.id,
                    avatar_image_id=image.id,
                )

                if old_avatar_image_id is not None:
                    await self.image_repo.delete(old_avatar_image_id)

            return user

        except Exception:
            try:
                await run_in_threadpool(self.storage.delete_object, s3_key)
            except Exception:
                pass
            raise

    async def remove_user_avatar(self, user: User):
        old_avatar_image_id = user.avatar_image_id
        if old_avatar_image_id is None:
            raise UserAvatarNotFoundError()

        image = await self.image_repo.get_by_id(old_avatar_image_id)
        if image is None:
            raise UserAvatarNotFoundError()

        async with self.uow:
            await self.user_repo.update(user.id, avatar_image_id=None)

            await self.image_repo.delete(old_avatar_image_id)


def build_listing_image_key(listing_id: UUID, content_type: str) -> str:
    ext = CONTENT_TYPE_TO_EXTENSION[content_type]
    return f"listings/{listing_id}/{uuid.uuid4()}.{ext}"


def build_avatar_key(user_id: UUID, content_type: str) -> str:
    ext = CONTENT_TYPE_TO_EXTENSION[content_type]
    return f"users/{user_id}/avatar/{uuid.uuid4()}.{ext}"
