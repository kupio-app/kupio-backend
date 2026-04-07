from src.core.exceptions import NotFoundError


class CategoryNotFoundError(NotFoundError):
    detail = "Category not found"


class InvalidParentProvided(NotFoundError):
    detail = "Invalid parent provided"
