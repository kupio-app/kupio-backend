from src.core.database.repositories import Repositories
from src.core.database.uow import UoW
from .exceptions import CategoryNotFoundError, InvalidParentProvided
from .repository import CategoriesRepository
from .models import Category
from .schemas import CategoryRequestCreate


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
        parent_category: Category | None = None
        if category_data.parent_id is not None:
            if (
                parent_category := await self.categories_repo.get_by_id(
                    category_data.parent_id
                )
            ) is None:
                raise InvalidParentProvided()

        async with self.uow:
            return await self.categories_repo.create(
                name=category_data.name,
                icon=category_data.icon,
                depth=0 if parent_category is None else parent_category.depth + 1,
                parent_id=category_data.parent_id,
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
