from fastapi import APIRouter, Depends, status

from src.core.dependencies import require_roles
from src.domains.users.enums import UserRole
from src.domains.categories.dependencies import get_category_by_id
from src.domains.categories.models import Category

from .dependencies import get_filter_def_by_id, get_filter_def_service
from .models import FilterDefinition
from .schemas import (
    FilterDefinitionRequest,
    FilterDefinitionResponse,
    FilterDefinitionUpdateRequest,
)
from .service import FilterDefinitionsService

router = APIRouter()


@router.get("", response_model=list[FilterDefinitionResponse])
async def get_filter_definitions(
    category: Category = Depends(get_category_by_id),  # Validate category existence
    service: FilterDefinitionsService = Depends(get_filter_def_service),
):
    return await service.get_definitions_for_category(category)


@router.post(
    "", response_model=FilterDefinitionResponse, status_code=status.HTTP_201_CREATED
)
async def create_filter_definition(
    data: FilterDefinitionRequest,
    category: Category = Depends(get_category_by_id),  # Validate category existence
    service: FilterDefinitionsService = Depends(get_filter_def_service),
    _=Depends(require_roles(UserRole.MODERATOR)),
):
    return await service.create_definition(
        category_id=category.id,
        slug=data.slug,
        label=data.label,
        filter_type=data.filter_type,
        options=data.options,
        is_required=data.is_required,
        display_order=data.display_order,
    )


@router.patch("/{filter_id}", response_model=FilterDefinitionResponse)
async def update_filter_definition(
    filter_data: FilterDefinitionUpdateRequest,
    definition: FilterDefinition = Depends(get_filter_def_by_id),
    service: FilterDefinitionsService = Depends(get_filter_def_service),
    _=Depends(require_roles(UserRole.MODERATOR)),
):
    return await service.update_definition(definition, filter_data)


@router.delete("/{filter_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_filter_definition(
    definition: FilterDefinition = Depends(get_filter_def_by_id),
    service: FilterDefinitionsService = Depends(get_filter_def_service),
    _=Depends(require_roles(UserRole.MODERATOR)),
):
    await service.delete_definition(definition.id)
