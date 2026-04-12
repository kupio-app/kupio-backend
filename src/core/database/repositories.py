from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.auth.repository import OAuthIdentitiesRepository, SessionsRepository
from src.domains.categories.repository import CategoriesRepository
from src.domains.chat.repository import ConversationsRepository, MessagesRepository
from src.domains.filter_definitions.repository import FilterDefinitionsRepository
from src.domains.favourites.repository import FavouritesRepository
from src.domains.images.repository import ImagesRepository, ListingImagesRepository
from src.domains.listings.repository import ListingsRepository
from src.domains.payments.repository import (
    BalanceTransactionRepository,
    PaymentSessionRepository,
)
from src.domains.promotions.repository import (
    ListingPromotionsRepository,
    PromotionPacketsRepository,
)
from src.domains.reports.repository import ReportReasonsRepository, ReportsRepository
from src.domains.users.repository import ModeratorsRepository, UsersRepository, NotificationTokensRepository


@dataclass(slots=True)
class Repositories:
    users: UsersRepository
    moderators: ModeratorsRepository
    sessions: SessionsRepository
    oauth_identities: OAuthIdentitiesRepository
    listings: ListingsRepository
    categories: CategoriesRepository
    filter_definitions: FilterDefinitionsRepository
    favourites: FavouritesRepository
    balance_transactions: BalanceTransactionRepository
    payments_sessions: PaymentSessionRepository
    promotion_packets: PromotionPacketsRepository
    listing_promotions: ListingPromotionsRepository
    conversations: ConversationsRepository
    messages: MessagesRepository
    notification_tokens: NotificationTokensRepository
    report_reasons: ReportReasonsRepository
    reports: ReportsRepository
    images: ImagesRepository
    listing_images: ListingImagesRepository

    @classmethod
    def from_session(cls, session: AsyncSession) -> "Repositories":
        return cls(
            users=UsersRepository(session=session),
            moderators=ModeratorsRepository(session=session),
            sessions=SessionsRepository(session=session),
            oauth_identities=OAuthIdentitiesRepository(session=session),
            listings=ListingsRepository(session=session),
            categories=CategoriesRepository(session=session),
            filter_definitions=FilterDefinitionsRepository(session=session),
            favourites=FavouritesRepository(session=session),
            balance_transactions=BalanceTransactionRepository(session=session),
            payments_sessions=PaymentSessionRepository(session=session),
            promotion_packets=PromotionPacketsRepository(session=session),
            listing_promotions=ListingPromotionsRepository(session=session),
            conversations=ConversationsRepository(session=session),
            messages=MessagesRepository(session=session),
            notification_tokens=NotificationTokensRepository(session=session),
            report_reasons=ReportReasonsRepository(session=session),
            reports=ReportsRepository(session=session),
            images=ImagesRepository(session=session),
            listing_images=ListingImagesRepository(session=session),
        )
