from fastapi import Depends

from src.core.database.uow import UoW
from src.core.dependencies import RepositoriesDeps, get_uow
from src.domains.categories.dependencies import (
    get_categories_service,
    get_category_by_id,
)
from src.domains.categories.service import CategoriesService
from src.domains.categories.models import Category
from .models import FilterDefinition
from .service import FilterDefinitionsService


def get_filter_def_service(
    repos: RepositoriesDeps,
    uow: UoW = Depends(get_uow),
    categories_service: CategoriesService = Depends(get_categories_service),
) -> FilterDefinitionsService:
    return FilterDefinitionsService(
        repos=repos, uow=uow, categories_service=categories_service
    )


async def get_filter_def_by_id(
    filter_id: int,
    category: Category = Depends(get_category_by_id),  # Validate category existence
    service: FilterDefinitionsService = Depends(get_filter_def_service),
) -> FilterDefinition:
    return await service.get_definition(category.id, filter_id)
