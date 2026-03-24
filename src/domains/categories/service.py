from src.core.database.repositories import Repositories
from src.core.database.uow import UoW
from .exceptions import CategoryNotFoundError
from .repository import CategoriesRepository
from .models import Category


class CategoriesService:
    def __init__(self, repos: Repositories, uow: UoW) -> None:
        self.repos = repos
        self.categories_repo: CategoriesRepository = repos.categories
        self.uow = uow

    async def get_categories(self, depth: int | None = None) -> list[Category]:
        if depth is None:
            return await self.categories_repo.get_all()

        return await self.categories_repo.get_by_depth(depth)

    async def get_category(self, category_id: int) -> Category:
        category = await self.categories_repo.get_by_id(category_id)
        if category is None:
            raise CategoryNotFoundError()

        return category

    async def get_subcategories(self, category_id: int) -> list[Category]:
        return await self.categories_repo.get_subcategories(category_id)

    async def get_breadcrumbs(self, category_id: int) -> list[Category]:
        return await self.categories_repo.get_breadcrumbs(category_id)
