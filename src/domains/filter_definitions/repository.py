from typing import Any

from sqlalchemy import ColumnElement

from src.core.database.base_repository import BaseRepository
from .enums import FilterType
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

    async def create(
        self,
        category_id: int,
        slug: str,
        label: str,
        filter_type: FilterType,
        options: dict | None,
        is_required: bool,
        display_order: int,
    ) -> FilterDefinition:
        return await self._add(
            FilterDefinition,
            category_id=category_id,
            slug=slug,
            label=label,
            filter_type=filter_type,
            options=options,
            is_required=is_required,
            display_order=display_order,
        )

    async def update_by_id(
        self, filter_id: int, **kwargs: Any
    ) -> FilterDefinition | None:
        return await self._update(
            FilterDefinition,
            [FilterDefinition.id == filter_id],
            **kwargs,
            load_result=True,
        )

    async def delete_by_id(self, filter_id: int) -> bool:
        return await self._delete(FilterDefinition, FilterDefinition.id == filter_id)
