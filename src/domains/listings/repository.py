import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select, and_, or_, cast, ColumnElement
from sqlalchemy.dialects.postgresql import JSONB

from src.core.database.base_repository import BaseRepository
from .enums import ListingStatus, CurrencyEnum
from .models import Listing


class ListingsRepository(BaseRepository):
    async def get_by_id(self, listing_id: UUID) -> Listing:
        return await self._get(Listing, Listing.id == listing_id)

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
        return await self._add(
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
            .order_by(Listing.created_at.desc(), Listing.id.desc())
            .limit(limit)
        )
        return list((await self.session.scalars(stmt)).unique())

    async def update_by_id(self, listing_id: UUID, **kwargs) -> Listing | None:
        result = await self._update(
            Listing, [Listing.id == listing_id], **kwargs, load_result=True
        )
        if result is not None:
            await self.session.refresh(result, ["category"])

        return result
