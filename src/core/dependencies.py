from typing import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from .database.repositories import Repositories
from .database.uow import UoW


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
