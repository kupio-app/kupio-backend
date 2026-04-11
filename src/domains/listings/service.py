from uuid import UUID

from src.core.database.repositories import Repositories
from src.core.database.uow import UoW
from src.core.utils.pagination import decode_cursor, encode_cursor
from src.domains.categories.service import CategoriesService
from src.domains.filter_definitions.service import FilterDefinitionsService
from src.domains.users.models import User
from .enums import ListingStatus
from .exceptions import ListingNotFoundError
from .models import Listing
from .repository import ListingsRepository
from .schemas import ListListingsResponse, ListingRequest, ListingResponse


class ListingsService:
    def __init__(
        self,
        repos: Repositories,
        uow: UoW,
        categories_service: CategoriesService,
        filter_definitions_service: FilterDefinitionsService,
    ) -> None:
        self.repos = repos
        self.listings_repo: ListingsRepository = repos.listings
        self.categories_service = categories_service
        self.filter_defs_service = filter_definitions_service
        self.uow = uow

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

        return ListListingsResponse(
            listings=[ListingResponse.model_validate(listing) for listing in listings],
            next_cursor=next_cursor,
        )

    async def get_listing(self, listing_id: UUID) -> Listing:
        if (listing := await self.listings_repo.get_by_id(listing_id)) is None:
            raise ListingNotFoundError()

        return listing

    async def get_listing_for_response(self, listing_id: UUID) -> Listing:
        if (
            listing := await self.listings_repo.get_for_response_by_id(listing_id)
        ) is None:
            raise ListingNotFoundError()

        return listing
