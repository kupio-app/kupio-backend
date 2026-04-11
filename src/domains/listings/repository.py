import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select, and_, or_, cast, ColumnElement, update, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import selectinload

from src.core.database.base_repository import BaseRepository
from src.domains.images.models import ListingImage
from .enums import ListingStatus, CurrencyEnum
from .models import Listing


class ListingsRepository(BaseRepository):
    @staticmethod
    def _response_read_options():
        return (
            selectinload(Listing.category),
            selectinload(Listing.images).joinedload(ListingImage.image),
        )

    async def get_by_id(
        self, listing_id: UUID, *, populate_existing: bool = False
    ) -> Listing:
        return await self._get(
            Listing,
            Listing.id == listing_id,
            populate_existing=populate_existing,
        )

    async def get_for_response_by_id(
        self, listing_id: UUID, *, populate_existing: bool = False
    ) -> Listing:
        return await self._get(
            Listing,
            Listing.id == listing_id,
            options=self._response_read_options(),
            populate_existing=populate_existing,
        )

    async def create(
        self,
        user_id: UUID,
        category_id: int,
        title: str,
        description: str,
        price: int,
        is_free: bool,
        is_tradable: bool,
        currency: CurrencyEnum,
        status: ListingStatus,
        custom_filters: dict | None = None,
    ) -> Listing:
        listing = await self._add(
            Listing,
            user_id=user_id,
            category_id=category_id,
            title=title,
            description=description,
            price=price,
            is_free=is_free,
            is_tradable=is_tradable,
            currency=currency,
            status=status,
            custom_filters=custom_filters,
        )
        listing_id = listing.id
        return await self.get_for_response_by_id(listing_id, populate_existing=True)

    async def search_all(
        self,
        user_id: UUID | None = None,
        status: ListingStatus | None = None,
        category_id: int | None = None,
        custom_filters: dict | None = None,
        limit: int = 20,
        cursor_created_at: datetime.datetime | None = None,
        cursor_id: UUID | None = None,
    ) -> list[Listing]:
        conditions: list[ColumnElement[Any]] = [Listing.deleted_at.is_(None)]

        if user_id is not None:
            conditions.append(Listing.user_id == user_id)

        if status is not None:
            conditions.append(Listing.status == status)

        if category_id is not None:
            conditions.append(Listing.category_id == category_id)

        if custom_filters:
            conditions.append(
                Listing.custom_filters.op("@>")(cast(custom_filters, JSONB))
            )

        if cursor_created_at is not None and cursor_id is not None:
            conditions.append(
                or_(
                    Listing.created_at < cursor_created_at,
                    and_(
                        Listing.created_at == cursor_created_at,
                        Listing.id < cursor_id,
                    ),
                )
            )

        stmt = (
            select(Listing)
            .where(*conditions)
            .options(*self._response_read_options())
            .order_by(Listing.created_at.desc(), Listing.id.desc())
            .limit(limit)
        )
        return list((await self.session.scalars(stmt)).unique())

    async def update_by_id(self, listing_id: UUID, **kwargs) -> Listing | None:
        await self._update(
            Listing, [Listing.id == listing_id], load_result=False, **kwargs
        )
        return await self.get_for_response_by_id(listing_id, populate_existing=True)

    async def soft_delete_by_id(self, listing_id: UUID) -> bool:
        return await self._soft_delete(Listing, Listing.id == listing_id)

    async def soft_delete_by_user_id(self, user_id: UUID) -> int:
        result = await self.session.execute(
            update(Listing)
            .where(
                Listing.user_id == user_id,
                Listing.deleted_at.is_(None),
            )
            .values(deleted_at=func.now())
        )
        await self.session.flush()
        return int(getattr(result, "rowcount", 0))
