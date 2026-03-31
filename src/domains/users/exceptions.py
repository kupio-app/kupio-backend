from src.core.exceptions import BadRequestError, ConflictError, NotFoundError


class UserNotFoundError(NotFoundError):
    detail = "User not found"


class UserPhoneConflictError(ConflictError):
    detail = "User with this phone already exists"


class UserUsernameConflictError(ConflictError):
    detail = "User with this username already exists"


class UsernameAlreadySetError(BadRequestError):
    detail = "Username is already set"
