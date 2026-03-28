from src.core.exceptions import NotFoundError, ConflictError, BadRequestError


class FilterDefinitionNotFoundError(NotFoundError):
    detail = "Filter definition not found"


class DuplicateFilterSlugError(ConflictError):
    detail = "A filter with this slug already exists for this category"


class InvalidCustomFiltersError(BadRequestError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
