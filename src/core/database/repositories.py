from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.auth.repository import OAuthIdentitiesRepository, SessionsRepository
from src.domains.categories.repository import CategoriesRepository
from src.domains.favourites.repository import FavouritesRepository
from src.domains.listings.repository import ListingsRepository
from src.domains.users.repository import UsersRepository


@dataclass(slots=True)
class Repositories:
    users: UsersRepository
    sessions: SessionsRepository
    oauth_identities: OAuthIdentitiesRepository
    listings: ListingsRepository
    categories: CategoriesRepository
    favourites: FavouritesRepository

    @classmethod
    def from_session(cls, session: AsyncSession) -> "Repositories":
        return cls(
            users=UsersRepository(session=session),
            sessions=SessionsRepository(session=session),
            oauth_identities=OAuthIdentitiesRepository(session=session),
            listings=ListingsRepository(session=session),
            categories=CategoriesRepository(session=session),
            favourites=FavouritesRepository(session=session),
        )
