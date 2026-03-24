from src.core.exceptions import NotFoundError


class CategoryNotFoundError(NotFoundError):
    detail = "Category not found"
