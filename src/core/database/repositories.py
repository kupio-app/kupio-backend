from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.auth.repository import SessionsRepository
from src.domains.categories.repository import CategoriesRepository
from src.domains.listings.repository import ListingsRepository
from src.domains.users.repository import UsersRepository


@dataclass(slots=True)
class Repositories:
    users: UsersRepository
    sessions: SessionsRepository
    listings: ListingsRepository
    categories: CategoriesRepository

    @classmethod
    def from_session(cls, session: AsyncSession) -> "Repositories":
        return cls(
            users=UsersRepository(session=session),
            sessions=SessionsRepository(session=session),
            listings=ListingsRepository(session=session),
            categories=CategoriesRepository(session=session),
        )
