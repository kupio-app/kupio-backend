from sqlalchemy import select

from src.core.database.base_repository import BaseRepository
from .models import Category


class CategoriesRepository(BaseRepository):
    async def get_by_id(self, category_id: int) -> Category | None:
        return await self._get(Category, Category.id == category_id)

    async def get_all(self) -> list[Category]:
        return await self._get_many(Category)

    async def get_by_depth(self, depth: int) -> list[Category]:
        return await self._get_many(Category, Category.depth == depth)

    async def get_subcategories(self, category_id: int) -> list[Category]:
        return await self._get_many(Category, Category.parent_id == category_id)

    async def get_breadcrumbs(self, category_id: int) -> list[Category]:
        base = (
            select(Category)
            .where(Category.id == category_id)
            .cte(name="breadcrumbs", recursive=True)
        )

        recursive = select(Category).join(base, Category.id == base.c.parent_id)

        cte = base.union_all(recursive)

        result = await self.session.execute(
            select(Category).join(cte, Category.id == cte.c.id)
        )

        categories = result.scalars().all()

        # Sort from root to current category
        category_map: dict[int, Category] = {c.id: c for c in categories}

        chain = []
        current = category_map.get(category_id)
        while current:
            chain.append(current)
            current = category_map.get(current.parent_id)

        return list(reversed(chain))  # [root, ..., current]
