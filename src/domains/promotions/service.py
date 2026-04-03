import datetime
from uuid import UUID

from src.core.database.repositories import Repositories
from src.core.database.uow import UoW
from src.core.utils.pagination import decode_cursor, encode_cursor
from src.domains.listings.enums import ListingStatus
from src.domains.listings.exceptions import ListingNotFoundError, ListingOwnershipError
from src.domains.payments.enums import TransactionType
from src.domains.payments.exceptions import InsufficientBalanceError
from src.domains.users.models import User
from .enums import PromotionStatus, PromotionType
from .exceptions import (
    DuplicateActivePromotionError,
    ListingNotPromotableError,
    ListingPromotionNotFoundError,
    PromotionPacketInactiveError,
    PromotionPacketNotFoundError,
)
from .models import ListingPromotion, PromotionPacket


class PromotionsService:
    def __init__(self, repos: Repositories, uow: UoW) -> None:
        self.repos = repos
        self.uow = uow

    async def list_packets(self) -> list[PromotionPacket]:
        return await self.repos.promotion_packets.get_all_active()

    async def get_packet(self, packet_id: int) -> PromotionPacket:
        packet = await self.repos.promotion_packets.get_by_id(packet_id)
        if packet is None:
            raise PromotionPacketNotFoundError()
        return packet

    async def create_packet(
        self,
        *,
        name: str,
        description: str | None,
        _type: PromotionType,
        duration_days: int,
        price: int,
    ) -> PromotionPacket:
        async with self.uow:
            return await self.repos.promotion_packets.create(
                name=name,
                description=description,
                _type=_type,
                duration_days=duration_days,
                price=price,
            )

    async def update_packet(self, packet_id: int, **kwargs) -> PromotionPacket:
        packet = await self.repos.promotion_packets.get_by_id(packet_id)
        if packet is None:
            raise PromotionPacketNotFoundError()

        async with self.uow:
            return await self.repos.promotion_packets.update(packet_id, **kwargs)

    async def purchase(
        self,
        current_user: User,
        listing_id: UUID,
        packet_id: int,
    ) -> ListingPromotion:
        listing = await self.repos.listings.get_by_id(listing_id)
        if listing is None:
            raise ListingNotFoundError()
        if listing.user_id != current_user.id:
            raise ListingOwnershipError()
        if listing.status != ListingStatus.ACTIVE:
            raise ListingNotPromotableError()

        packet = await self.repos.promotion_packets.get_by_id(packet_id)
        if packet is None:
            raise PromotionPacketNotFoundError()
        if not packet.is_active:
            raise PromotionPacketInactiveError()

        existing = await self.repos.listing_promotions.get_active_by_listing_and_type(
            listing_id, packet.type
        )
        if existing is not None:
            raise DuplicateActivePromotionError()

        now = datetime.datetime.now(datetime.UTC)
        expires_at = now + datetime.timedelta(days=packet.duration_days)

        async with self.uow:
            success = await self.repos.users.deduct_balance(
                current_user.id, packet.price
            )
            if not success:
                raise InsufficientBalanceError()

            transaction = await self.repos.balance_transactions.create(
                user_id=current_user.id,
                amount=-packet.price,
                type=TransactionType.DEBIT,
            )

            return await self.repos.listing_promotions.create(
                listing_id=listing_id,
                packet_id=packet_id,
                transaction_id=transaction.id,
                starts_at=now,
                expires_at=expires_at,
                status=PromotionStatus.ACTIVE,
            )

    async def list_for_listing(
        self, current_user: User, listing_id: UUID
    ) -> list[ListingPromotion]:
        listing = await self.repos.listings.get_by_id(listing_id)
        if listing is None:
            raise ListingNotFoundError()
        if listing.user_id != current_user.id:
            raise ListingOwnershipError()

        return await self.repos.listing_promotions.get_active_for_listing(listing_id)

    async def list_my_promotions(
        self,
        current_user: User,
        *,
        limit: int,
        cursor: str | None = None,
    ) -> tuple[list[ListingPromotion], str | None]:
        cursor_created_at, cursor_id = decode_cursor(cursor) if cursor else (None, None)

        promotions = await self.repos.listing_promotions.get_by_user(
            current_user.id,
            limit=limit,
            cursor_created_at=cursor_created_at,
            cursor_id=cursor_id,
        )

        next_cursor = (
            encode_cursor(promotions[-1].created_at, promotions[-1].id)
            if len(promotions) == limit
            else None
        )

        return promotions, next_cursor

    async def get_promotion(self, promotion_id: UUID) -> ListingPromotion:
        promotion = await self.repos.listing_promotions.get_by_id(promotion_id)
        if promotion is None:
            raise ListingPromotionNotFoundError()
        return promotion
