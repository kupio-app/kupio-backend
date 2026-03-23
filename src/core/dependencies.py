from typing import Annotated, AsyncGenerator, Callable, Awaitable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from src.core.config import get_config
from src.core.database.repositories import Repositories
from src.core.database.uow import UoW
from src.core.security import decode_access_token
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


RepositoriesDeps = Annotated[Repositories, Depends(get_repo)]


async def get_current_user(
    repos: RepositoriesDeps,
    token: str = Depends(oauth2_scheme),
) -> User:
    config = get_config()

    try:
        user_id = decode_access_token(token=token, config=config.auth)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=401, detail="Invalid token") from exc

    if not isinstance(user_id, str):
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = await repos.users.get_by_id_str(user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    return user


def require_roles(*allowed_roles: str) -> Callable[..., Awaitable[User]]:
    async def _checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return _checker
