import datetime
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import ColumnElement, and_, or_, select
from sqlalchemy.orm import selectinload

from src.core.database.base_repository import BaseRepository
from src.domains.images.models import ListingImage
from src.domains.listings.models import Listing

from .models import ListingFavourite


@dataclass(slots=True)
class FavouritedListing:
    listing: Listing
    favourited_at: datetime.datetime
    listing_id: UUID


class FavouritesRepository(BaseRepository):
    @staticmethod
    def _listing_response_read_options():
        return (
            selectinload(Listing.category),
            selectinload(Listing.images).joinedload(ListingImage.image),
        )

    async def get_by_user_and_listing(
        self,
        *,
        user_id: UUID,
        listing_id: UUID,
    ) -> ListingFavourite | None:
        return await self._get(
            ListingFavourite,
            ListingFavourite.user_id == user_id,
            ListingFavourite.listing_id == listing_id,
        )

    async def create(self, *, user_id: UUID, listing_id: UUID) -> ListingFavourite:
        return await self._add(
            ListingFavourite,
            user_id=user_id,
            listing_id=listing_id,
        )

    async def delete(self, *, user_id: UUID, listing_id: UUID) -> bool:
        return await self._delete(
            ListingFavourite,
            ListingFavourite.user_id == user_id,
            ListingFavourite.listing_id == listing_id,
        )

    async def get_favourited_listings_ids(self, user_id) -> list[UUID]:
        return await self._get_many(
            ListingFavourite.listing_id, ListingFavourite.user_id == user_id
        )

    async def list_favourited_listings(
        self,
        *,
        user_id: UUID,
        limit: int,
        cursor_created_at: datetime.datetime | None = None,
        cursor_id: UUID | None = None,
    ) -> list[FavouritedListing]:
        conditions: list[ColumnElement[Any]] = [
            ListingFavourite.user_id == user_id,
            Listing.deleted_at.is_(None),
        ]

        if cursor_created_at is not None and cursor_id is not None:
            conditions.append(
                or_(
                    ListingFavourite.created_at < cursor_created_at,
                    and_(
                        ListingFavourite.created_at == cursor_created_at,
                        ListingFavourite.listing_id < cursor_id,
                    ),
                )
            )

        stmt = (
            select(Listing, ListingFavourite.created_at)
            .join(ListingFavourite, ListingFavourite.listing_id == Listing.id)
            .where(*conditions)
            .options(*self._listing_response_read_options())
            .order_by(
                ListingFavourite.created_at.desc(),
                ListingFavourite.listing_id.desc(),
            )
            .limit(limit)
        )

        rows = (await self.session.execute(stmt)).all()
        return [
            FavouritedListing(
                listing=listing,
                favourited_at=favourited_at,
                listing_id=listing.id,
            )
            for listing, favourited_at in rows
        ]
