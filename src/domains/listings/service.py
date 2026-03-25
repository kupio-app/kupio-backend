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
        self, limit: int = 100, offset: int = 0
    ) -> ListListingsResponse:
        listings: list[Listing] = await self.listings_repo.list_all(
            status=ListingStatus.ACTIVE, limit=limit, offset=offset
        )
        return ListListingsResponse(
            listings=[ListingResponse.model_validate(x) for x in listings],
            total=len(listings),
        )

    async def get_listing(self, listing_id: UUID) -> Listing:
        if (listing := await self.listings_repo.get_by_id(listing_id)) is None:
            raise ListingNotFoundError()

        return listing
