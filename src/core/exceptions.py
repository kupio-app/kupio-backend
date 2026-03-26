from starlette import status


class DomainError(Exception):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Domain error"

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail or self.detail
        super().__init__(self.detail)


class BadRequestError(DomainError):
    status_code = status.HTTP_400_BAD_REQUEST


class UnauthorizedError(DomainError):
    status_code = status.HTTP_401_UNAUTHORIZED


class ForbiddenError(DomainError):
    status_code = status.HTTP_403_FORBIDDEN


class NotFoundError(DomainError):
    status_code = status.HTTP_404_NOT_FOUND


class ConflictError(DomainError):
    status_code = status.HTTP_409_CONFLICT
