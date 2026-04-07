from src.core.database.repositories import Repositories
from src.core.database.uow import UoW
from .exceptions import (
    CategoryNotFoundError,
    InvalidParentProvided,
    CircularCategoryReferenceError,
)
from .repository import CategoriesRepository
from .models import Category
from .schemas import CategoryRequestCreate, CategoryRequestUpdate


class CategoriesService:
    def __init__(self, repos: Repositories, uow: UoW) -> None:
        self.repos = repos
        self.categories_repo: CategoriesRepository = repos.categories
        self.uow = uow

    async def get_categories(
        self,
        depth: int | None = None,
        *,
        limit: int,
        offset: int = 0,
    ) -> list[Category]:
        if depth is None:
            return await self.categories_repo.get_all(limit=limit, offset=offset)

        return await self.categories_repo.get_by_depth(
            depth,
            limit=limit,
            offset=offset,
        )

    async def create_category(self, category_data: CategoryRequestCreate) -> Category:
        parent_category = await self._check_parent(category_data.parent_id)

        async with self.uow:
            return await self.categories_repo.create(
                name=category_data.name,
                icon=category_data.icon,
                depth=0 if parent_category is None else parent_category.depth + 1,
                parent_id=category_data.parent_id,
            )

    async def update_category(
        self, category_data: CategoryRequestUpdate, category: Category
    ) -> Category:
        depth = category.depth
        if category_data.parent_id != category.parent_id:
            if category_data.parent_id is not None:
                if category_data.parent_id == category.id:
                    raise CircularCategoryReferenceError()

                ancestor_ids = await self.categories_repo.get_ancestor_ids(
                    category_data.parent_id
                )
                if category.id in ancestor_ids:
                    raise CircularCategoryReferenceError()

            parent_category = await self._check_parent(category_data.parent_id)
            depth = 0 if parent_category is None else parent_category.depth + 1

        async with self.uow:
            return await self.categories_repo.update(
                category_id=category.id,
                **category_data.model_dump(exclude_unset=True),
                depth=depth,
            )

    async def get_category(self, category_id: int) -> Category:
        category = await self.categories_repo.get_by_id(category_id)
        if category is None:
            raise CategoryNotFoundError()

        return category

    async def get_subcategories(
        self, category_id: int, *, limit: int, offset: int = 0
    ) -> list[Category]:
        return await self.categories_repo.get_subcategories(
            category_id,
            limit=limit,
            offset=offset,
        )

    async def get_breadcrumbs(self, category_id: int) -> list[Category]:
        return await self.categories_repo.get_breadcrumbs(category_id)

    async def _check_parent(self, parent_id: int | None) -> Category | None:
        parent_category: Category | None = None
        if parent_id is not None:
            if (
                parent_category := await self.categories_repo.get_by_id(parent_id)
            ) is None:
                raise InvalidParentProvided()

        return parent_category
