from dataclasses import dataclass
from typing import Annotated, AsyncGenerator, Callable, Awaitable, TypeAlias

from fastapi import Depends, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from src.core.config import get_config
from src.core.database.repositories import Repositories
from src.core.database.uow import UoW
from src.core.security import decode_access_token
from src.domains.auth.exceptions import (
    InsufficientPermissionsError,
    InvalidTokenError,
    InvalidTokenPayloadError,
)
from src.domains.users.models import User


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login"
)  # Used for OpenAPI documentation and token extraction from requests


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


@dataclass
class PaginationParams:
    limit: int = Query(20, gt=0, lt=200)
    cursor: str | None = None


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


def require_roles(*allowed_roles: str) -> Callable[..., Awaitable[User]]:
    async def _checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise InsufficientPermissionsError()
        return current_user

    return _checker
