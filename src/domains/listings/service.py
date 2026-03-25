import base64
import json
import datetime
from uuid import UUID

from src.core.database.repositories import Repositories
from src.core.database.uow import UoW
from src.domains.categories.service import CategoriesService
from src.domains.users.models import User
from .enums import ListingStatus
from .exceptions import ListingNotFoundError
from .models import Listing
from .repository import ListingsRepository
from .schemas import ListListingsResponse, ListingResponse, ListingRequest


def _decode_cursor(cursor: str) -> tuple[datetime.datetime, UUID]:
    data = json.loads(base64.urlsafe_b64decode(cursor))
    return datetime.datetime.fromisoformat(data["created_at"]), UUID(data["id"])


def _encode_cursor(listing: Listing) -> str:
    data = {"created_at": listing.created_at.isoformat(), "id": str(listing.id)}
    return base64.urlsafe_b64encode(json.dumps(data).encode()).decode()


class ListingsService:
    def __init__(
        self, repos: Repositories, uow: UoW, categories_service: CategoriesService
    ) -> None:
        self.repos = repos
        self.listings_repo: ListingsRepository = repos.listings
        self.categories_service = categories_service
        self.uow = uow

    async def create_listing(
        self, current_user: User, listing_data: ListingRequest
    ) -> Listing:
        await self.categories_service.get_category(listing_data.category_id)
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
            )

    async def update_listing_status(
        self, listing_id: UUID, new_status: ListingStatus
    ) -> Listing:
        async with self.uow:
            return await self.listings_repo.update_by_id(listing_id, status=new_status)

    async def update(self, listing_id: UUID, listing_data: ListingRequest) -> Listing:
        await self.categories_service.get_category(listing_data.category_id)
        async with self.uow:
            return await self.listings_repo.update_by_id(
                listing_id,
                category_id=listing_data.category_id,
                title=listing_data.title,
                description=listing_data.description,
                price=listing_data.price,
                is_free=listing_data.is_free,
                is_tradable=listing_data.is_tradable,
                currency=listing_data.currency,
            )

    async def list_all_active(
        self, limit: int = 20, cursor: str | None = None
    ) -> ListListingsResponse:
        cursor_created_at, cursor_id = (
            _decode_cursor(cursor) if cursor else (None, None)
        )
        listings: list[Listing] = await self.listings_repo.search_all(
            status=ListingStatus.ACTIVE,
            limit=limit,
            cursor_created_at=cursor_created_at,
            cursor_id=cursor_id,
        )
        next_cursor = _encode_cursor(listings[-1]) if len(listings) == limit else None
        return ListListingsResponse(
            listings=[ListingResponse.model_validate(x) for x in listings],
            next_cursor=next_cursor,
        )

    async def get_listing(self, listing_id: UUID) -> Listing:
        if (listing := await self.listings_repo.get_by_id(listing_id)) is None:
            raise ListingNotFoundError()

        return listing
