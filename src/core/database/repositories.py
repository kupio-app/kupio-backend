from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from .base_repository import BaseRepository


@dataclass(slots=True)
class Repositories:
    users: BaseRepository

    @classmethod
    def from_session(cls, session: AsyncSession) -> "Repositories":
        return cls(users=BaseRepository(session=session))
