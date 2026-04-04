from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.auth.repository import OAuthIdentitiesRepository, SessionsRepository
from src.domains.categories.repository import CategoriesRepository
from src.domains.filter_definitions.repository import FilterDefinitionsRepository
from src.domains.favourites.repository import FavouritesRepository
from src.domains.listings.repository import ListingsRepository
from src.domains.payments.repository import BalanceTransactionRepository
from src.domains.promotions.repository import (
    ListingPromotionsRepository,
    PromotionPacketsRepository,
)
from src.domains.users.repository import UsersRepository


@dataclass(slots=True)
class Repositories:
    users: UsersRepository
    sessions: SessionsRepository
    oauth_identities: OAuthIdentitiesRepository
    listings: ListingsRepository
    categories: CategoriesRepository
    filter_definitions: FilterDefinitionsRepository
    favourites: FavouritesRepository
    balance_transactions: BalanceTransactionRepository
    promotion_packets: PromotionPacketsRepository
    listing_promotions: ListingPromotionsRepository

    @classmethod
    def from_session(cls, session: AsyncSession) -> "Repositories":
        return cls(
            users=UsersRepository(session=session),
            sessions=SessionsRepository(session=session),
            oauth_identities=OAuthIdentitiesRepository(session=session),
            listings=ListingsRepository(session=session),
            categories=CategoriesRepository(session=session),
            filter_definitions=FilterDefinitionsRepository(session=session),
            favourites=FavouritesRepository(session=session),
            balance_transactions=BalanceTransactionRepository(session=session),
            promotion_packets=PromotionPacketsRepository(session=session),
            listing_promotions=ListingPromotionsRepository(session=session),
        )
