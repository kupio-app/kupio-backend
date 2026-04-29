import datetime
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select, and_, or_, cast, case, ColumnElement, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import selectinload

from src.core.database.base_repository import BaseRepository
from src.domains.chat.models import Conversation
from src.domains.favourites.models import ListingFavourite
from src.domains.images.models import ListingImage
from src.domains.promotions.enums import PromotionStatus
from src.domains.promotions.models import ListingPromotion
from .enums import CurrencyEnum, ListingStatus
from .models import Listing, ListingView


@dataclass(slots=True)
class OwnerListingStats:
    listing: Listing
    seen_count: int
    favourites_count: int
    chats_count: int
    promotion_expires_at: datetime.datetime | None

    @property
    def is_promoted(self) -> bool:
        return self.promotion_expires_at is not None


@dataclass(slots=True)
class OwnerDashboardStats:
    active_count: int
    inactive_count: int
    promoted_count: int
    chats_count: int
    favourites_count: int


class ListingsRepository(BaseRepository):
    @staticmethod
    def _response_read_options():
        return (
            selectinload(Listing.category),
            selectinload(Listing.images).joinedload(ListingImage.image),
        )

    @staticmethod
    def _effective_price_expression():
        return case((Listing.is_free.is_(True), 0), else_=Listing.price)

    @staticmethod
    def _escape_like_pattern(value: str) -> str:
        return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

    @staticmethod
    def _search_conditions(
        *,
        user_id: UUID | None = None,
        status: ListingStatus | None = None,
        q: str | None = None,
        category_id: int | None = None,
        min_price: int | None = None,
        max_price: int | None = None,
        is_free: bool | None = None,
        is_tradable: bool | None = None,
        custom_filters: dict | None = None,
        cursor_created_at: datetime.datetime | None = None,
        cursor_id: UUID | None = None,
    ) -> list[ColumnElement[Any]]:
        conditions: list[ColumnElement[Any]] = [Listing.deleted_at.is_(None)]

        if user_id is not None:
            conditions.append(Listing.user_id == user_id)

        if status is not None:
            conditions.append(Listing.status == status)

        if q is not None:
            pattern = f"%{ListingsRepository._escape_like_pattern(q)}%"
            conditions.append(
                or_(
                    Listing.title.ilike(pattern, escape="\\"),
                    Listing.description.ilike(pattern, escape="\\"),
                )
            )

        if category_id is not None:
            conditions.append(Listing.category_id == category_id)

        if is_free is not None:
            conditions.append(Listing.is_free.is_(is_free))

        if is_tradable is not None:
            conditions.append(Listing.is_tradable.is_(is_tradable))

        if min_price is not None or max_price is not None:
            effective_price = ListingsRepository._effective_price_expression()
            if min_price is not None:
                conditions.append(effective_price >= min_price)
            if max_price is not None:
                conditions.append(effective_price <= max_price)

        if custom_filters:
            conditions.append(
                Listing.custom_filters.op("@>")(cast(custom_filters, JSONB))
            )

        if cursor_created_at is not None and cursor_id is not None:
            conditions.append(
                or_(
                    Listing.created_at < cursor_created_at,
                    and_(
                        Listing.created_at == cursor_created_at,
                        Listing.id < cursor_id,
                    ),
                )
            )

        return conditions

    async def get_by_id(
        self, listing_id: UUID, *, populate_existing: bool = False
    ) -> Listing:
        return await self._get(
            Listing,
            Listing.id == listing_id,
            populate_existing=populate_existing,
        )

    async def get_for_response_by_id(
        self, listing_id: UUID, *, populate_existing: bool = False
    ) -> Listing:
        return await self._get(
            Listing,
            Listing.id == listing_id,
            options=self._response_read_options(),
            populate_existing=populate_existing,
        )

    async def create(
        self,
        user_id: UUID,
        category_id: int,
        title: str,
        description: str,
        price: int,
        is_free: bool,
        is_tradable: bool,
        currency: CurrencyEnum,
        status: ListingStatus,
        custom_filters: dict | None = None,
    ) -> Listing:
        listing = await self._add(
            Listing,
            user_id=user_id,
            category_id=category_id,
            title=title,
            description=description,
            price=price,
            is_free=is_free,
            is_tradable=is_tradable,
            currency=currency,
            status=status,
            custom_filters=custom_filters,
        )
        listing_id = listing.id
        return await self.get_for_response_by_id(listing_id, populate_existing=True)

    async def search_all(
        self,
        user_id: UUID | None = None,
        status: ListingStatus | None = None,
        q: str | None = None,
        category_id: int | None = None,
        min_price: int | None = None,
        max_price: int | None = None,
        is_free: bool | None = None,
        is_tradable: bool | None = None,
        custom_filters: dict | None = None,
        limit: int = 20,
        cursor_created_at: datetime.datetime | None = None,
        cursor_id: UUID | None = None,
    ) -> list[Listing]:
        conditions = self._search_conditions(
            user_id=user_id,
            status=status,
            q=q,
            category_id=category_id,
            min_price=min_price,
            max_price=max_price,
            is_free=is_free,
            is_tradable=is_tradable,
            custom_filters=custom_filters,
            cursor_created_at=cursor_created_at,
            cursor_id=cursor_id,
        )

        stmt = (
            select(Listing)
            .where(*conditions)
            .options(*self._response_read_options())
            .order_by(Listing.created_at.desc(), Listing.id.desc())
            .limit(limit)
        )
        return list((await self.session.scalars(stmt)).unique())

    async def search_all_with_owner_stats(
        self,
        *,
        user_id: UUID,
        status: ListingStatus | None = None,
        limit: int = 20,
        cursor_created_at: datetime.datetime | None = None,
        cursor_id: UUID | None = None,
    ) -> list[OwnerListingStats]:
        conditions = self._search_conditions(
            user_id=user_id,
            status=status,
            cursor_created_at=cursor_created_at,
            cursor_id=cursor_id,
        )
        page_listing_ids = (
            select(
                Listing.id.label("listing_id"),
                Listing.created_at.label("created_at"),
            )
            .where(*conditions)
            .order_by(Listing.created_at.desc(), Listing.id.desc())
            .limit(limit)
            .cte("page_listing_ids")
        )
        seen_counts = (
            select(
                ListingView.listing_id.label("listing_id"),
                func.count(ListingView.id).label("seen_count"),
            )
            .join(
                page_listing_ids,
                page_listing_ids.c.listing_id == ListingView.listing_id,
            )
            .group_by(ListingView.listing_id)
            .subquery()
        )
        favourites_counts = (
            select(
                ListingFavourite.listing_id.label("listing_id"),
                func.count().label("favourites_count"),
            )
            .join(
                page_listing_ids,
                page_listing_ids.c.listing_id == ListingFavourite.listing_id,
            )
            .group_by(ListingFavourite.listing_id)
            .subquery()
        )
        chats_counts = (
            select(
                Conversation.listing_id.label("listing_id"),
                func.count(Conversation.id).label("chats_count"),
            )
            .join(
                page_listing_ids,
                page_listing_ids.c.listing_id == Conversation.listing_id,
            )
            .group_by(Conversation.listing_id)
            .subquery()
        )
        promotion_expiry = (
            select(
                ListingPromotion.listing_id.label("listing_id"),
                func.max(ListingPromotion.expires_at).label("promotion_expires_at"),
            )
            .join(
                page_listing_ids,
                page_listing_ids.c.listing_id == ListingPromotion.listing_id,
            )
            .where(
                ListingPromotion.status == PromotionStatus.ACTIVE,
                ListingPromotion.expires_at > func.now(),
            )
            .group_by(ListingPromotion.listing_id)
            .subquery()
        )

        stmt = (
            select(
                Listing,
                func.coalesce(seen_counts.c.seen_count, 0).label("seen_count"),
                func.coalesce(favourites_counts.c.favourites_count, 0).label(
                    "favourites_count"
                ),
                func.coalesce(chats_counts.c.chats_count, 0).label("chats_count"),
                promotion_expiry.c.promotion_expires_at,
            )
            .join(page_listing_ids, page_listing_ids.c.listing_id == Listing.id)
            .outerjoin(seen_counts, seen_counts.c.listing_id == Listing.id)
            .outerjoin(
                favourites_counts,
                favourites_counts.c.listing_id == Listing.id,
            )
            .outerjoin(chats_counts, chats_counts.c.listing_id == Listing.id)
            .outerjoin(promotion_expiry, promotion_expiry.c.listing_id == Listing.id)
            .options(*self._response_read_options())
            .order_by(page_listing_ids.c.created_at.desc(), Listing.id.desc())
        )
        rows = (await self.session.execute(stmt)).unique().all()
        return [
            OwnerListingStats(
                listing=listing,
                seen_count=int(seen_count),
                favourites_count=int(favourites_count),
                chats_count=int(chats_count),
                promotion_expires_at=promotion_expires_at,
            )
            for listing, seen_count, favourites_count, chats_count, promotion_expires_at in rows
        ]

    async def get_owner_dashboard_stats(self, user_id: UUID) -> OwnerDashboardStats:
        owned_listing_conditions = [
            Listing.user_id == user_id,
            Listing.deleted_at.is_(None),
        ]
        stmt = select(
            select(func.count(Listing.id))
            .where(*owned_listing_conditions, Listing.status == ListingStatus.ACTIVE)
            .scalar_subquery()
            .label("active_count"),
            select(func.count(Listing.id))
            .where(
                *owned_listing_conditions,
                Listing.status == ListingStatus.INACTIVE,
            )
            .scalar_subquery()
            .label("inactive_count"),
            select(func.count(func.distinct(ListingPromotion.listing_id)))
            .select_from(ListingPromotion)
            .join(Listing, Listing.id == ListingPromotion.listing_id)
            .where(
                *owned_listing_conditions,
                ListingPromotion.status == PromotionStatus.ACTIVE,
                ListingPromotion.expires_at > func.now(),
            )
            .scalar_subquery()
            .label("promoted_count"),
            select(func.count(Conversation.id))
            .select_from(Conversation)
            .join(Listing, Listing.id == Conversation.listing_id)
            .where(*owned_listing_conditions)
            .scalar_subquery()
            .label("chats_count"),
            select(func.count())
            .select_from(ListingFavourite)
            .join(Listing, Listing.id == ListingFavourite.listing_id)
            .where(*owned_listing_conditions)
            .scalar_subquery()
            .label("favourites_count"),
        )
        row = (await self.session.execute(stmt)).one()
        return OwnerDashboardStats(
            active_count=int(row.active_count),
            inactive_count=int(row.inactive_count),
            promoted_count=int(row.promoted_count),
            chats_count=int(row.chats_count),
            favourites_count=int(row.favourites_count),
        )

    async def update_by_id(self, listing_id: UUID, **kwargs) -> Listing | None:
        await self._update(
            Listing, [Listing.id == listing_id], load_result=False, **kwargs
        )
        return await self.get_for_response_by_id(listing_id, populate_existing=True)

    async def soft_delete_by_id(self, listing_id: UUID) -> bool:
        return await self._soft_delete(Listing, Listing.id == listing_id)

    async def soft_delete_by_user_id(self, user_id: UUID) -> int:
        return await self._soft_delete(
            Listing,
            Listing.user_id == user_id,
            return_rowcount=True,
        )


class ListingViewsRepository(BaseRepository):
    async def count_by_listing_id(self, listing_id: UUID) -> int:
        stmt = select(func.count(ListingView.id)).where(
            ListingView.listing_id == listing_id
        )
        return int((await self.session.scalar(stmt)) or 0)

    async def create(
        self,
        *,
        listing_id: UUID,
        viewer_user_id: UUID | None,
    ) -> ListingView:
        return await self._add(
            ListingView,
            listing_id=listing_id,
            viewer_user_id=viewer_user_id,
        )
