import datetime
from uuid import UUID

from src.core.database.repositories import Repositories
from src.core.database.uow import UoW
from src.core.utils.pagination import decode_cursor, encode_cursor
from src.domains.listings.enums import ListingStatus
from src.domains.listings.models import Listing
from src.domains.payments.enums import TransactionType
from src.domains.payments.exceptions import InsufficientBalanceError
from src.domains.users.models import User
from .enums import PromotionStatus
from .exceptions import (
    DuplicateActivePromotionError,
    ListingNotPromotableError,
    ListingPromotionNotFoundError,
    PromotionPacketInactiveError,
    PromotionPacketNotFoundError,
)
from .models import ListingPromotion, PromotionPacket
from .schemas import (
    ListPromotionsResponse,
    ListingPromotionResponse,
    PromotionPacketCreateRequest,
    PromotionPacketUpdateRequest,
)


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
        self, packet_data: PromotionPacketCreateRequest
    ) -> PromotionPacket:
        async with self.uow:
            return await self.repos.promotion_packets.create(
                name=packet_data.name,
                description=packet_data.description,
                _type=packet_data.type,
                duration_days=packet_data.duration_days,
                price=packet_data.price,
            )

    async def update_packet(
        self, packet_id: int, packet_data: PromotionPacketUpdateRequest
    ) -> PromotionPacket:
        async with self.uow:
            return await self.repos.promotion_packets.update(
                packet_id, **packet_data.model_dump(exclude_unset=True)
            )

    async def purchase(
        self,
        current_user: User,
        listing: Listing,
        packet_id: int,
    ) -> ListingPromotion:
        packet = await self.get_packet(packet_id)
        await self._validate_purchase(listing, packet)

        async with self.uow:
            success = await self.repos.users.deduct_balance(
                current_user.id, packet.price
            )
            if not success:
                raise InsufficientBalanceError()

            transaction = await self.repos.balance_transactions.create(
                user_id=current_user.id,
                amount=-packet.price,
                _type=TransactionType.DEBIT,
            )

            return await self._create_listing_promotion(
                listing,
                packet,
                transaction_id=transaction.id,
            )

    async def _validate_purchase(
        self, listing: Listing, packet: PromotionPacket
    ) -> None:
        if listing.status != ListingStatus.ACTIVE:
            raise ListingNotPromotableError()

        if not packet.is_active:
            raise PromotionPacketInactiveError()

        existing = await self.repos.listing_promotions.get_active_by_listing_and_type(
            listing.id, packet.type
        )
        if existing is not None:
            raise DuplicateActivePromotionError()

    async def _create_listing_promotion(
        self,
        listing: Listing,
        packet: PromotionPacket,
        *,
        transaction_id: UUID,
    ) -> ListingPromotion:
        now = datetime.datetime.now(datetime.UTC)
        expires_at = now + datetime.timedelta(days=packet.duration_days)
        return await self.repos.listing_promotions.create(
            listing_id=listing.id,
            packet_id=packet.id,
            transaction_id=transaction_id,
            starts_at=now,
            expires_at=expires_at,
            status=PromotionStatus.ACTIVE,
        )

    async def list_for_listing(self, listing: Listing) -> list[ListingPromotion]:
        return await self.repos.listing_promotions.get_active_for_listing(listing.id)

    async def list_my_promotions(
        self,
        current_user_id: UUID,
        *,
        limit: int,
        cursor: str | None = None,
    ) -> ListPromotionsResponse:
        cursor_created_at, cursor_id = decode_cursor(cursor) if cursor else (None, None)

        promotions = await self.repos.listing_promotions.get_by_user(
            current_user_id,
            limit=limit,
            cursor_created_at=cursor_created_at,
            cursor_id=cursor_id,
        )

        next_cursor = (
            encode_cursor(promotions[-1].created_at, promotions[-1].id)
            if len(promotions) == limit
            else None
        )

        return ListPromotionsResponse(
            promotions=[ListingPromotionResponse.model_validate(x) for x in promotions],
            next_cursor=next_cursor,
        )

    async def get_promotion(self, promotion_id: UUID) -> ListingPromotion:
        promotion = await self.repos.listing_promotions.get_by_id(promotion_id)
        if promotion is None:
            raise ListingPromotionNotFoundError()

        return promotion
