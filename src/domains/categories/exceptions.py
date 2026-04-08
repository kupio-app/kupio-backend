from src.core.exceptions import BadRequestError, NotFoundError


class CategoryNotFoundError(NotFoundError):
    detail = "Category not found"


class InvalidParentProvided(NotFoundError):
    detail = "Invalid parent provided"


class CircularCategoryReferenceError(BadRequestError):
    detail = "Setting this parent would create a circular reference"
