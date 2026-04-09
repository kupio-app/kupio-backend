import datetime

from uuid import UUID
from sqlalchemy import select, update, and_, or_, func

from src.core.database.base_repository import BaseRepository
from src.domains.listings.models import Listing

from .enums import PromotionType, PromotionStatus
from .models import PromotionPacket, ListingPromotion


class PromotionPacketsRepository(BaseRepository):
    async def get_by_id(self, packet_id: int) -> PromotionPacket | None:
        return await self._get(PromotionPacket, PromotionPacket.id == packet_id)

    async def get_all_active(self) -> list[PromotionPacket]:
        return await self._get_many(
            PromotionPacket, PromotionPacket.is_active.is_(True)
        )

    async def create(
        self,
        *,
        name: str,
        description: str | None,
        _type: PromotionType,
        duration_days: int,
        price: int,
    ) -> PromotionPacket:
        return await self._add(
            PromotionPacket,
            name=name,
            description=description,
            type=_type,
            duration_days=duration_days,
            price=price,
        )

    async def update(self, packet_id: int, **kwargs) -> PromotionPacket | None:
        return await self._update(
            PromotionPacket, [PromotionPacket.id == packet_id], **kwargs
        )


class ListingPromotionsRepository(BaseRepository):
    async def create(
        self,
        *,
        listing_id: UUID,
        packet_id: int,
        transaction_id: UUID,
        starts_at: datetime.datetime,
        expires_at: datetime.datetime,
        status: PromotionStatus,
    ) -> ListingPromotion:
        result = await self._add(
            ListingPromotion,
            listing_id=listing_id,
            packet_id=packet_id,
            transaction_id=transaction_id,
            starts_at=starts_at,
            expires_at=expires_at,
            status=status,
        )
        await self.session.refresh(
            result, attribute_names=["packet", "listing", "transaction"]
        )
        return result

    async def get_by_id(self, promotion_id: UUID) -> ListingPromotion | None:
        return await self._get(ListingPromotion, ListingPromotion.id == promotion_id)

    async def get_active_by_listing_and_type(
        self, listing_id: UUID, type: PromotionType
    ) -> ListingPromotion | None:
        return await self._get(
            ListingPromotion,
            ListingPromotion.listing_id == listing_id,
            ListingPromotion.status == PromotionStatus.ACTIVE,
            ListingPromotion.expires_at > func.now(),
            ListingPromotion.packet.has(PromotionPacket.type == type),
        )

    async def get_active_for_listing(self, listing_id: UUID) -> list[ListingPromotion]:
        return await self._get_many(
            ListingPromotion,
            ListingPromotion.listing_id == listing_id,
            ListingPromotion.status == PromotionStatus.ACTIVE,
            ListingPromotion.expires_at > func.now(),
        )

    async def get_by_user(
        self,
        user_id: UUID,
        *,
        limit: int,
        cursor_created_at: datetime.datetime | None = None,
        cursor_id: UUID | None = None,
    ) -> list[ListingPromotion]:
        conditions = [
            Listing.user_id == user_id,
            Listing.deleted_at.is_(None),
        ]

        if cursor_created_at is not None and cursor_id is not None:
            conditions.append(
                or_(
                    ListingPromotion.created_at < cursor_created_at,
                    and_(
                        ListingPromotion.created_at == cursor_created_at,
                        ListingPromotion.id < cursor_id,
                    ),
                )
            )

        stmt = (
            select(ListingPromotion)
            .join(Listing, ListingPromotion.listing_id == Listing.id)
            .where(*conditions)
            .order_by(ListingPromotion.created_at.desc(), ListingPromotion.id.desc())
            .limit(limit)
        )
        return await self._scalars_all(stmt)

    async def bulk_expire(self) -> int:
        result = await self.session.execute(
            update(ListingPromotion)
            .where(
                ListingPromotion.status == PromotionStatus.ACTIVE,
                ListingPromotion.expires_at <= func.now(),
            )
            .values(status=PromotionStatus.EXPIRED)
        )
        await self.session.flush()
        return result.rowcount
