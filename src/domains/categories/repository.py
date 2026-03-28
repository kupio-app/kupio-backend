from typing import Any

from sqlalchemy import select, literal, ColumnElement

from src.core.database.base_repository import BaseRepository
from .models import Category


class CategoriesRepository(BaseRepository):
    _SORTING_BY: tuple[ColumnElement[Any]] = (Category.name,)

    async def get_by_id(self, category_id: int) -> Category | None:
        return await self._get(Category, Category.id == category_id)

    async def get_all(self, *, limit: int, offset: int = 0) -> list[Category]:
        return await self._get_many(
            Category, limit=limit, offset=offset, order_by=self._SORTING_BY
        )

    async def get_by_depth(
        self, depth: int, *, limit: int, offset: int = 0
    ) -> list[Category]:
        return await self._get_many(
            Category,
            Category.depth == depth,
            limit=limit,
            offset=offset,
            order_by=self._SORTING_BY,
        )

    async def get_subcategories(
        self, category_id: int, *, limit: int, offset: int = 0
    ) -> list[Category]:
        return await self._get_many(
            Category,
            Category.parent_id == category_id,
            limit=limit,
            offset=offset,
            order_by=self._SORTING_BY,
        )

    async def get_breadcrumbs(self, category_id: int) -> list[Category]:
        base = (
            select(Category, literal(0).label("level"))
            .where(Category.id == category_id)
            .cte(name="breadcrumbs", recursive=True)
        )

        recursive = select(Category, (base.c.level + 1).label("level")).join(
            base, Category.id == base.c.parent_id
        )

        cte = base.union_all(recursive)

        result = await self.session.execute(
            select(Category)
            .join(cte, Category.id == cte.c.id)
            .order_by(cte.c.level.desc())
        )

        return list(result.scalars().unique())
