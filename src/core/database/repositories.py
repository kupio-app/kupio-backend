from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.users.repository import UsersRepository


@dataclass(slots=True)
class Repositories:
    users: UsersRepository

    @classmethod
    def from_session(cls, session: AsyncSession) -> "Repositories":
        return cls(users=UsersRepository(session=session))
