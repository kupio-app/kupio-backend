from src.core.database.repositories import Repositories
from src.core.database.uow import UoW
from src.domains.categories.service import CategoriesService
from src.domains.categories.models import Category
from .enums import FilterType
from .exceptions import (
    DuplicateFilterSlugError,
    FilterDefinitionNotFoundError,
    InvalidCustomFiltersError,
)
from .models import FilterDefinition
from .repository import FilterDefinitionsRepository
from .schemas import FilterDefinitionUpdateRequest
from .utils import validate_filter_value, validate_select_options


class FilterDefinitionsService:
    def __init__(
        self, repos: Repositories, uow: UoW, categories_service: CategoriesService
    ) -> None:
        self.repo: FilterDefinitionsRepository = repos.filter_definitions
        self.uow = uow
        self.categories_service = categories_service

    async def get_definitions_for_category(
        self, category: Category
    ) -> list[FilterDefinition]:
        # Category existence checked before in router
        return await self.repo.get_by_category_id(category.id)

    async def get_definition(
        self, category_id: int, filter_id: int
    ) -> FilterDefinition:
        if (definition := await self.repo.get_by_id(filter_id)) is None:
            raise FilterDefinitionNotFoundError()

        if definition.category_id != category_id:
            raise FilterDefinitionNotFoundError()

        return definition

    async def create_definition(
        self,
        category_id: int,
        slug: str,
        label: str,
        filter_type: FilterType,
        options: dict | None,
        is_required: bool,
        display_order: int,
    ) -> FilterDefinition:
        # Category existence checked before in router
        if await self.repo.get_by_category_and_slug(category_id, slug) is not None:
            raise DuplicateFilterSlugError()

        async with self.uow:
            return await self.repo.create(
                category_id=category_id,
                slug=slug,
                label=label,
                filter_type=filter_type,
                options=options,
                is_required=is_required,
                display_order=display_order,
            )

    async def update_definition(
        self, definition: FilterDefinition, filter_data: FilterDefinitionUpdateRequest
    ) -> FilterDefinition:
        # Check about filter def existence already processed in router

        new_slug = filter_data.slug
        if new_slug is not None and new_slug != definition.slug:
            if (
                await self.repo.get_by_category_and_slug(
                    definition.category_id, new_slug
                )
                is not None
            ):
                raise DuplicateFilterSlugError()

        # Get filter_type and options after applying the update,
        # then validate that SELECT always has a valid options.values
        resolved_filter_type = filter_data.filter_type or definition.filter_type
        resolved_options = filter_data.options or definition.options
        if resolved_filter_type == FilterType.SELECT:
            try:
                validate_select_options(resolved_options)
            except ValueError as e:
                raise InvalidCustomFiltersError(str(e)) from e

        async with self.uow:
            return await self.repo.update_by_id(
                definition.id, **filter_data.model_dump(exclude_unset=True)
            )

    async def delete_definition(self, filter_id: int) -> None:
        # Check about filter def existence already processed in router
        async with self.uow:
            await self.repo.delete_by_id(filter_id)

    async def validate_custom_filters(
        self, category_id: int, custom_filters: dict | None
    ) -> None:
        definitions = await self.repo.get_by_category_id(category_id)
        if not definitions:
            return

        definitions_by_slug = {d.slug: d for d in definitions}
        if custom_filters is None:
            custom_filters = {}

        unknown_keys = set(custom_filters.keys()) - set(definitions_by_slug.keys())
        if unknown_keys:
            raise InvalidCustomFiltersError(
                f"Unknown filter keys: {', '.join(sorted(unknown_keys))}"
            )

        for definition in definitions:
            if definition.is_required and definition.slug not in custom_filters:
                raise InvalidCustomFiltersError(
                    f"Filter '{definition.slug}' is required"
                )

        for slug, value in custom_filters.items():
            definition = definitions_by_slug[slug]
            validate_filter_value(slug, value, definition)
