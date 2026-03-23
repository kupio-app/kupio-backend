from src.core.exceptions import ConflictError, NotFoundError


class UserNotFoundError(NotFoundError):
    detail = "User not found"


class UserPhoneConflictError(ConflictError):
    detail = "User with this phone already exists"
