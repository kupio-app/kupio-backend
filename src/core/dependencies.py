from typing import Annotated, AsyncGenerator, Callable, Awaitable, TypeAlias

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from src.core.config import get_config
from src.core.database.repositories import Repositories
from src.core.database.uow import UoW
from src.core.security import decode_access_token
from src.core.storage.s3 import S3StorageService
from src.domains.auth.exceptions import (
    InsufficientPermissionsError,
    InvalidTokenError,
    InvalidTokenPayloadError,
)
from src.domains.users.enums import UserRole
from src.domains.users.models import Moderator, User


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login"
)  # Used for OpenAPI documentation and token extraction from requests
optional_oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login", auto_error=False
)


def get_redis(request: Request) -> Redis:
    return request.app.state.redis


async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    async with request.app.state.db_session_factory() as session:
        yield session
        # await session.commit()


async def get_repo(
    session: AsyncSession = Depends(get_db_session),
) -> Repositories:
    return Repositories.from_session(session=session)


async def get_uow(session: AsyncSession = Depends(get_db_session)) -> UoW:
    return UoW(session=session)


RepositoriesDeps: TypeAlias = Annotated[Repositories, Depends(get_repo)]


async def get_current_user(
    repos: RepositoriesDeps,
    token: str = Depends(oauth2_scheme),
) -> User:
    config = get_config()

    try:
        user_id = decode_access_token(token=token, config=config.auth)
    except Exception as exc:  # pragma: no cover
        raise InvalidTokenError() from exc

    if not isinstance(user_id, str):
        raise InvalidTokenPayloadError()

    user = await repos.users.get_by_id_str(user_id)
    if user is None:
        raise InvalidTokenError()

    return user


async def get_current_user_or_none(
    repos: RepositoriesDeps,
    token: str | None = Depends(optional_oauth2_scheme),
) -> User | None:
    """Return the authenticated user, or ``None`` for anonymous requests.

    This dependency is intended for public endpoints that can benefit from viewer
    context but must remain accessible to anonymous clients. Missing, stale, or
    malformed tokens are treated as anonymous and return ``None`` instead of
    raising an authentication error.
    """
    if token is None:
        return None

    try:
        return await get_current_user(repos=repos, token=token)
    except InvalidTokenError, InvalidTokenPayloadError:
        return None


def require_roles(*allowed_roles: str) -> Callable[..., Awaitable[User]]:
    async def _checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise InsufficientPermissionsError()
        return current_user

    return _checker


async def get_current_moderator(
    repos: RepositoriesDeps,
    current_user: User = Depends(require_roles(UserRole.MODERATOR)),
) -> Moderator:
    moderator = await repos.moderators.get_by_user_id(current_user.id)
    if moderator is None:
        raise InsufficientPermissionsError()

    return moderator


def get_s3_storage_service(request: Request) -> S3StorageService:
    return request.app.state.s3_storage
