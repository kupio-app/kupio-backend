from uuid import UUID

from src.core.database.repositories import Repositories
from src.core.database.uow import UoW
from src.core.utils.pagination import (
    decode_cursor,
    encode_cursor,
    decode_ranked_cursor,
    encode_ranked_cursor,
)
from src.domains.categories.service import CategoriesService
from src.domains.filter_definitions.service import FilterDefinitionsService
from src.domains.users.models import User
from .consts import SPONSORED_LISTINGS_LIMIT
from .enums import ListingStatus
from .exceptions import ListingNotFoundError
from .models import Listing
from .repository import ListingsRepository, OwnerDashboardStats, ListingWithPromotions
from .schemas import (
    ListListingsResponse,
    ListOwnerListingsResponse,
    ListingRequest,
    ListingDetailResponse,
    ListingResponse,
    OwnerListingResponse,
)
from ..promotions.enums import PromotionType


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
                phone=listing_data.phone,
                contact_name=listing_data.contact_name,
                is_calls_disabled=listing_data.is_calls_disabled,
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
                phone=listing_data.phone,
                contact_name=listing_data.contact_name,
                is_calls_disabled=listing_data.is_calls_disabled,
            )

    async def list_listings(
        self,
        user_id: UUID | None = None,
        status: ListingStatus | None = None,
        q: str | None = None,
        category_id: int | None = None,
        min_price: int | None = None,
        max_price: int | None = None,
        is_free: bool | None = None,
        is_tradable: bool | None = None,
        custom_filters: dict | None = None,
        limit: int = 20,
        cursor: str | None = None,
    ) -> ListListingsResponse:
        cursor_rank, cursor_created_at, cursor_id = (
            decode_ranked_cursor(cursor) if cursor else (None, None, None)
        )
        results: list[ListingWithPromotions] = await self.listings_repo.search_all(
            user_id=user_id,
            status=status,
            q=q,
            category_id=category_id,
            min_price=min_price,
            max_price=max_price,
            is_free=is_free,
            is_tradable=is_tradable,
            custom_filters=custom_filters,
            limit=limit,
            cursor_rank=cursor_rank,
            cursor_created_at=cursor_created_at,
            cursor_id=cursor_id,
        )
        next_cursor = (
            encode_ranked_cursor(
                results[-1].promotion_rank,
                results[-1].listing.created_at,
                results[-1].listing.id,
            )
            if len(results) == limit
            else None
        )

        sponsored: list[Listing] | None = None
        if (
            category_id is not None and cursor is None
        ):  # Populated only on the first page
            sponsored = await self.listings_repo.get_sponsored(
                category_id, limit=SPONSORED_LISTINGS_LIMIT
            )

        return ListListingsResponse(
            listings=[
                ListingResponse.model_validate(r.listing).model_copy(
                    update={"active_promotions": r.active_promotions}
                )
                for r in results
            ],
            sponsored=[
                ListingResponse.model_validate(x).model_copy(
                    update={"active_promotions": [PromotionType.VIP]}
                )
                for x in sponsored
            ],
            next_cursor=next_cursor,
        )

    async def get_listing(self, listing_id: UUID) -> Listing:
        if (listing := await self.listings_repo.get_by_id(listing_id)) is None:
            raise ListingNotFoundError()

        return listing

    async def list_owned_listings(
        self,
        user_id: UUID,
        *,
        status: ListingStatus | None = None,
        limit: int = 20,
        cursor: str | None = None,
    ) -> ListOwnerListingsResponse:
        cursor_created_at, cursor_id = decode_cursor(cursor) if cursor else (None, None)
        listings = await self.listings_repo.search_all_with_owner_stats(
            user_id=user_id,
            status=status,
            limit=limit,
            cursor_created_at=cursor_created_at,
            cursor_id=cursor_id,
        )
        next_cursor = (
            encode_cursor(listings[-1].listing.created_at, listings[-1].listing.id)
            if len(listings) == limit
            else None
        )

        return ListOwnerListingsResponse(
            listings=[OwnerListingResponse.build_from(listing) for listing in listings],
            next_cursor=next_cursor,
        )

    async def get_owner_dashboard_stats(self, user_id: UUID) -> OwnerDashboardStats:
        return await self.listings_repo.get_owner_dashboard_stats(user_id)

    async def get_listing_for_response(
        self,
        listing_id: UUID,
        *,
        current_user: User | None = None,
        count_seen: bool = False,
    ) -> ListingDetailResponse:
        if (
            listing := await self.listings_repo.get_for_response_by_id(listing_id)
        ) is None:
            raise ListingNotFoundError()

        if self._should_count_seen(
            listing=listing,
            current_user=current_user,
            count_seen=count_seen,
        ):
            async with self.uow:
                await self.repos.listing_views.create(
                    listing_id=listing.id,
                    viewer_user_id=(
                        current_user.id if current_user is not None else None
                    ),
                )

        seen_count = await self.repos.listing_views.count_by_listing_id(listing.id)

        active_promotions_data = (
            await self.repos.listing_promotions.get_active_for_listing(listing.id)
        )
        active_promotions = [p.packet.type for p in active_promotions_data]

        phone, contact_name = None, None
        if current_user is not None:
            if not listing.is_calls_disabled:
                phone = listing.phone or listing.user.phone
                contact_name = listing.contact_name or listing.user.display_name

        base = ListingResponse.model_validate(listing)
        return ListingDetailResponse.model_construct(
            **base.model_dump(),
            active_promotions=active_promotions,
            seen_count=seen_count,
            phone=phone,
            contact_name=contact_name,
        )

    @staticmethod
    def _should_count_seen(
        *,
        listing: Listing,
        current_user: User | None,
        count_seen: bool,
    ) -> bool:
        if not count_seen or listing.status != ListingStatus.ACTIVE:
            return False

        return current_user is None or current_user.id != listing.user_id
