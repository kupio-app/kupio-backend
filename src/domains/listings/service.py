from uuid import UUID

from collections import defaultdict

from src.core.database.repositories import Repositories
from src.core.database.uow import UoW
from src.core.storage.s3 import S3StorageService
from src.core.utils.pagination import decode_cursor, encode_cursor
from src.domains.categories.service import CategoriesService
from src.domains.filter_definitions.service import FilterDefinitionsService
from src.domains.images.schemas import ListingImageResponse
from src.domains.users.models import User
from .enums import ListingStatus
from .exceptions import ListingNotFoundError
from .models import Listing
from .repository import ListingsRepository
from .schemas import ListListingsResponse, ListingResponse, ListingRequest


class ListingsService:
    def __init__(
        self,
        repos: Repositories,
        uow: UoW,
        categories_service: CategoriesService,
        filter_definitions_service: FilterDefinitionsService,
        storage: S3StorageService,
    ) -> None:
        self.repos = repos
        self.listings_repo: ListingsRepository = repos.listings
        self.listing_images_repo = repos.listing_images
        self.categories_service = categories_service
        self.filter_defs_service = filter_definitions_service
        self.uow = uow
        self.storage = storage

    async def to_listing_response(self, listing: Listing) -> ListingResponse:
        listing_images = await self.listing_images_repo.get_images_for_listing(
            listing.id
        )
        images = [
            ListingImageResponse(
                id=image.id,
                url=self.storage.build_public_url(image.s3_key),
                sort_order=listing_image.sort_order,
            )
            for listing_image, image in listing_images
        ]
        data = ListingResponse.model_validate(listing)
        data.images = images
        return data

    async def create_listing(
        self, current_user: User, listing_data: ListingRequest
    ) -> Listing:
        await self.categories_service.get_category(listing_data.category_id)
        await self.filter_defs_service.validate_custom_filters(
            listing_data.category_id, listing_data.custom_filters
        )
        async with self.uow:
            return await self.listings_repo.create(
                user_id=current_user.id,
                category_id=listing_data.category_id,
                title=listing_data.title,
                description=listing_data.description,
                price=listing_data.price,
                is_free=listing_data.is_free,
                is_tradable=listing_data.is_tradable,
                currency=listing_data.currency,
                status=ListingStatus.INACTIVE,
                custom_filters=listing_data.custom_filters,
            )

    async def update_listing_status(
        self, listing_id: UUID, new_status: ListingStatus
    ) -> Listing:
        async with self.uow:
            return await self.listings_repo.update_by_id(listing_id, status=new_status)

    async def update_listing(
        self, listing: Listing, listing_data: ListingRequest
    ) -> Listing:
        if listing.category_id != listing_data.category_id:
            # Check only if category changed
            await self.categories_service.get_category(listing_data.category_id)

        if (
            listing.category_id != listing_data.category_id
            or listing.custom_filters != listing_data.custom_filters
        ):
            # Check only if custom_filters or category changed
            await self.filter_defs_service.validate_custom_filters(
                listing_data.category_id, listing_data.custom_filters
            )

        async with self.uow:
            return await self.listings_repo.update_by_id(
                listing_id=listing.id,
                category_id=listing_data.category_id,
                title=listing_data.title,
                description=listing_data.description,
                price=listing_data.price,
                is_free=listing_data.is_free,
                is_tradable=listing_data.is_tradable,
                currency=listing_data.currency,
                custom_filters=listing_data.custom_filters,
            )

    async def list_listings(
        self,
        user_id: UUID | None = None,
        status: ListingStatus | None = None,
        category_id: int | None = None,
        custom_filters: dict | None = None,
        limit: int = 20,
        cursor: str | None = None,
    ) -> ListListingsResponse:
        cursor_created_at, cursor_id = decode_cursor(cursor) if cursor else (None, None)
        listings: list[Listing] = await self.listings_repo.search_all(
            user_id=user_id,
            status=status,
            category_id=category_id,
            custom_filters=custom_filters,
            limit=limit,
            cursor_created_at=cursor_created_at,
            cursor_id=cursor_id,
        )
        next_cursor = (
            encode_cursor(listings[-1].created_at, listings[-1].id)
            if len(listings) == limit
            else None
        )

        listing_ids = [l.id for l in listings]
        rows = await self.listing_images_repo.get_images_for_listings(listing_ids)
        images_by_listing_id: dict[UUID, list[ListingImageResponse]] = defaultdict(list)
        for listing_image, image in rows:
            images_by_listing_id[listing_image.listing_id].append(
                ListingImageResponse(
                    id=image.id,
                    url=self.storage.build_public_url(image.s3_key),
                    sort_order=listing_image.sort_order,
                )
            )

        listing_responses: list[ListingResponse] = []
        for listing in listings:
            data = ListingResponse.model_validate(listing)
            data.images = images_by_listing_id.get(listing.id, [])
            listing_responses.append(data)

        return ListListingsResponse(
            listings=listing_responses,
            next_cursor=next_cursor,
        )

    async def get_listing(self, listing_id: UUID) -> Listing:
        if (listing := await self.listings_repo.get_by_id(listing_id)) is None:
            raise ListingNotFoundError()

        return listing
