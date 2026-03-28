from fastapi import Depends

from src.core.database.uow import UoW
from src.core.dependencies import RepositoriesDeps, get_uow
from .models import Category
from .service import CategoriesService


def get_categories_service(
    repos: RepositoriesDeps,
    uow: UoW = Depends(get_uow),
) -> CategoriesService:
    return CategoriesService(repos=repos, uow=uow)


async def get_category_by_id(
    category_id: int,
    service: CategoriesService = Depends(get_categories_service),
) -> Category:
    return await service.get_category(category_id)
