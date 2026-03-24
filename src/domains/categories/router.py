from fastapi import APIRouter, Depends

from .dependencies import get_categories_service, get_category_by_id
from .models import Category
from .schemas import CategoryResponse
from .service import CategoriesService

router = APIRouter()


@router.get("", response_model=list[CategoryResponse])
async def get_categories(
    depth: int | None = None,
    service: CategoriesService = Depends(get_categories_service),
):
    return await service.get_categories(depth=depth)


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(category: Category = Depends(get_category_by_id)):
    return category


@router.get("/{category_id}/subcategories", response_model=list[CategoryResponse])
async def get_subcategories(
    category: Category = Depends(get_category_by_id),
    service: CategoriesService = Depends(get_categories_service),
):
    return await service.get_subcategories(category.id)


@router.get("/{category_id}/breadcrumbs", response_model=list[CategoryResponse])
async def get_category_breadcrumbs(
    category: Category = Depends(get_category_by_id),
    service: CategoriesService = Depends(get_categories_service),
):
    return await service.get_breadcrumbs(category.id)
