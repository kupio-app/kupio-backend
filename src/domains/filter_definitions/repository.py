from typing import Any

from sqlalchemy import ColumnElement

from src.core.database.base_repository import BaseRepository
from .models import FilterDefinition


class FilterDefinitionsRepository(BaseRepository):
    _SORTING_BY: tuple[ColumnElement[Any]] = (FilterDefinition.display_order,)

    async def get_by_id(self, filter_id: int) -> FilterDefinition | None:
        return await self._get(FilterDefinition, FilterDefinition.id == filter_id)

    async def get_by_category_id(self, category_id: int) -> list[FilterDefinition]:
        return await self._get_many(
            FilterDefinition,
            FilterDefinition.category_id == category_id,
            order_by=self._SORTING_BY,
        )

    async def get_by_category_and_slug(
        self, category_id: int, slug: str
    ) -> FilterDefinition | None:
        return await self._get(
            FilterDefinition,
            FilterDefinition.category_id == category_id,
            FilterDefinition.slug == slug,
        )

    async def create(self, **kwargs: Any) -> FilterDefinition:
        return await self._add(FilterDefinition, **kwargs)

    async def update_by_id(
        self, filter_id: int, **kwargs: Any
    ) -> FilterDefinition | None:
        return await self._update(
            FilterDefinition, [FilterDefinition.id == filter_id], **kwargs
        )

    async def delete_by_id(self, filter_id: int) -> bool:
        return await self._delete(FilterDefinition, FilterDefinition.id == filter_id)
