from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.auth.repository import SessionsRepository
from src.domains.users.repository import UsersRepository


@dataclass(slots=True)
class Repositories:
    users: UsersRepository
    sessions: SessionsRepository

    @classmethod
    def from_session(cls, session: AsyncSession) -> "Repositories":
        return cls(
            users=UsersRepository(session=session),
            sessions=SessionsRepository(session=session),
        )
