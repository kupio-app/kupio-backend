import datetime
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Index, String, DateTime
from sqlalchemy.orm import Mapped as M, mapped_column as mc, relationship

from src.core.database.base_model import Base, UUID, Int64
from src.domains.promotions.enums import PromotionType, PromotionStatus

if TYPE_CHECKING:
    from src.domains.listings.models import Listing
    from src.domains.payments.models import BalanceTransaction


class PromotionPacket(Base):
    __tablename__ = "promotion_packets"

    id: M[Int64] = mc(primary_key=True, autoincrement=True)
    name: M[str] = mc(String(100))
    description: M[str | None] = mc(String(255))
    type: M[PromotionType] = mc(Enum(PromotionType))
    duration_days: M[int]
    price: M[Int64]  # in cents
    is_active: M[bool] = mc(default=True)


class ListingPromotion(Base):
    __tablename__ = "listing_promotions"

    __table_args__ = (
        Index("ix_listing_promotions_status_expires_at", "status", "expires_at"),
    )

    id: M[UUID] = mc(primary_key=True, default=uuid.uuid4)
    listing_id: M[UUID] = mc(
        ForeignKey("listings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    listing: M["Listing"] = relationship("Listing", lazy="joined")
    packet_id: M[Int64] = mc(ForeignKey("promotion_packets.id"), nullable=False)
    packet: M["PromotionPacket"] = relationship("PromotionPacket", lazy="joined")
    transaction_id: M[UUID] = mc(ForeignKey("balance_transactions.id"), nullable=False)
    transaction: M["BalanceTransaction"] = relationship(
        "BalanceTransaction", lazy="joined"
    )
    starts_at: M[datetime.datetime] = mc(DateTime(timezone=True))
    expires_at: M[datetime.datetime] = mc(DateTime(timezone=True))
    status: M[PromotionStatus] = mc(Enum(PromotionStatus))
