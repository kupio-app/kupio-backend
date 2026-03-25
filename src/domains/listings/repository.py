from typing import Any
from uuid import UUID

from sqlalchemy import ColumnExpressionArgument

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
        )

    async def list_all(
        self,
        user_id: UUID | None = None,
        status: ListingStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Listing]:
        conditions: list[ColumnExpressionArgument[Any]] = []
        if user_id is not None:
            conditions.append(Listing.user_id == user_id)

        if status is not None:
            conditions.append(Listing.status == status)

        return await self._get_many(Listing, *conditions)

    async def update_by_id(self, listing_id: UUID, **kwargs) -> Listing | None:
        return await self._update(
            Listing, [Listing.id == listing_id], **kwargs, load_result=True
        )
