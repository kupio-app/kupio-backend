from src.core.exceptions import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
)


class InvalidCredentialsError(UnauthorizedError):
    detail = "Invalid credentials"


class InvalidGoogleTokenError(UnauthorizedError):
    detail = "Invalid Google token"


class InvalidRefreshTokenError(UnauthorizedError):
    detail = "Invalid or expired refresh token"


class EmailAlreadyTakenError(ConflictError):
    detail = "Email already taken"


class UsernameAlreadyTakenError(ConflictError):
    detail = "Username already taken"


class SessionNotFoundError(NotFoundError):
    detail = "Session not found"


class NewPasswordMustDifferError(BadRequestError):
    detail = "New password must be different from current password"


class InvalidCurrentPasswordError(UnauthorizedError):
    detail = "Invalid current password"


class PasswordAlreadySetError(ConflictError):
    detail = "Password is already set for this account"


class InvalidTokenError(UnauthorizedError):
    detail = "Invalid token"


class InvalidTokenPayloadError(UnauthorizedError):
    detail = "Invalid token payload"


class InsufficientPermissionsError(ForbiddenError):
    detail = "Insufficient permissions"
