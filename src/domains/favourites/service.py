from uuid import UUID

from sqlalchemy.exc import IntegrityError

from src.core.database.repositories import Repositories
from src.core.database.uow import UoW
from src.core.utils.pagination import decode_cursor, encode_cursor
from src.domains.listings.exceptions import ListingNotFoundError
from src.domains.listings.repository import ListingsRepository
from src.domains.listings.schemas import ListListingsResponse, ListingResponse
from src.domains.users.models import User

from .exceptions import (
    CannotFavouriteOwnListingError,
    ListingAlreadyFavouritedError,
    ListingNotInFavouritesError,
)
from .repository import FavouritesRepository


class FavouritesService:
    def __init__(self, repos: Repositories, uow: UoW) -> None:
        self.repos = repos
        self.listings_repo: ListingsRepository = repos.listings
        self.favourites_repo: FavouritesRepository = repos.favourites
        self.uow = uow

    async def add_favourite(self, current_user: User, listing_id: UUID) -> None:
        listing = await self.listings_repo.get_by_id(listing_id)
        if listing is None:
            raise ListingNotFoundError()

        if listing.user_id == current_user.id:
            raise CannotFavouriteOwnListingError()

        if await self._favourite_exists(current_user.id, listing_id):
            raise ListingAlreadyFavouritedError()

        try:
            async with self.uow:
                await self.favourites_repo.create(
                    user_id=current_user.id,
                    listing_id=listing_id,
                )
        except IntegrityError as exc:
            if await self._favourite_exists(current_user.id, listing_id):
                raise ListingAlreadyFavouritedError() from exc
            raise

    async def remove_favourite(self, current_user: User, listing_id: UUID) -> None:
        async with self.uow:
            deleted = await self.favourites_repo.delete(
                user_id=current_user.id,
                listing_id=listing_id,
            )

        if not deleted:
            raise ListingNotInFavouritesError()

    async def list_favourites(
        self,
        current_user: User,
        *,
        limit: int,
        cursor: str | None = None,
    ) -> ListListingsResponse:
        cursor_created_at, cursor_id = decode_cursor(cursor) if cursor else (None, None)
        favourites = await self.favourites_repo.list_favourited_listings(
            user_id=current_user.id,
            limit=limit,
            cursor_created_at=cursor_created_at,
            cursor_id=cursor_id,
        )
        next_cursor = (
            encode_cursor(favourites[-1].favourited_at, favourites[-1].listing_id)
            if len(favourites) == limit
            else None
        )
        return ListListingsResponse(
            listings=[ListingResponse.model_validate(x.listing) for x in favourites],
            next_cursor=next_cursor,
        )

    async def _favourite_exists(self, user_id: UUID, listing_id: UUID) -> bool:
        favourite = await self.favourites_repo.get_by_user_and_listing(
            user_id=user_id,
            listing_id=listing_id,
        )
        return favourite is not None
