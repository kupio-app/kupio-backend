from fastapi import APIRouter, Depends

from src.core.utils.pagination import LimitOffsetPaginationParams
from src.core.dependencies import require_roles
from src.domains.users.enums import UserRole

from .dependencies import get_categories_service, get_category_by_id
from .models import Category
from .schemas import CategoryResponse, CategorySlim, CategoryRequestCreate
from .service import CategoriesService

router = APIRouter()


@router.post("", response_model=CategoryResponse)
async def create_category(
    category_data: CategoryRequestCreate,
    service: CategoriesService = Depends(get_categories_service),
    _=Depends(require_roles(UserRole.MODERATOR)),
):
    return await service.create_category(category_data)


@router.get("", response_model=list[CategoryResponse])
async def get_categories(
    depth: int | None = None,
    pagination: LimitOffsetPaginationParams = Depends(),
    service: CategoriesService = Depends(get_categories_service),
):
    return await service.get_categories(
        depth=depth,
        limit=pagination.limit,
        offset=pagination.offset,
    )


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(category: Category = Depends(get_category_by_id)):
    return category


@router.get("/{category_id}/subcategories", response_model=list[CategoryResponse])
async def get_subcategories(
    category: Category = Depends(get_category_by_id),
    pagination: LimitOffsetPaginationParams = Depends(),
    service: CategoriesService = Depends(get_categories_service),
):
    return await service.get_subcategories(
        category.id,
        limit=pagination.limit,
        offset=pagination.offset,
    )


@router.get("/{category_id}/breadcrumbs", response_model=list[CategorySlim])
async def get_category_breadcrumbs(
    category: Category = Depends(get_category_by_id),
    service: CategoriesService = Depends(get_categories_service),
):
    return await service.get_breadcrumbs(category.id)
