import uuid
import datetime

from sqlalchemy import String, ForeignKey, UniqueConstraint, Index, Enum, DateTime, func
from sqlalchemy.orm import Mapped as M, mapped_column as mc, relationship

from src.core.database.base_model import Base, UUID
from src.core.database.mixins import SoftDeleteMixin

from .enums import DevicePlatform


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        UniqueConstraint(
            "listing_id", "buyer_id", name="uq_conversation_listing_buyer"
        ),
        Index("ix_conversations_buyer_id", "buyer_id"),
        Index("ix_conversations_seller_id", "seller_id"),
        Index("ix_conversations_listing_id", "listing_id"),
    )

    id: M[UUID] = mc(primary_key=True, default=uuid.uuid4)
    listing_id: M[UUID] = mc(
        ForeignKey("listings.id", ondelete="CASCADE"), nullable=False
    )
    buyer_id: M[UUID] = mc(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    seller_id: M[UUID] = mc(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    messages: M[list["Message"]] = relationship(
        "Message", back_populates="conversation", lazy="noload"
    )


class Message(Base, SoftDeleteMixin):
    __tablename__ = "messages"
    __table_args__ = (
        Index(
            "ix_messages_conversation_id_created_at", "conversation_id", "created_at"
        ),
    )

    id: M[UUID] = mc(primary_key=True, default=uuid.uuid4)
    conversation_id: M[UUID] = mc(
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender_id: M[UUID] = mc(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    body: M[str] = mc(String(4000))

    conversation: M["Conversation"] = relationship(
        "Conversation", back_populates="messages", lazy="noload"
    )


class DeviceToken(Base):
    __tablename__ = "device_tokens"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "platform", "token", name="uq_device_token_user_platform_token"
        ),
        Index("ix_device_tokens_user_id", "user_id"),
    )

    id: M[UUID] = mc(primary_key=True, default=uuid.uuid4)
    user_id: M[UUID] = mc(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token: M[str] = mc(String(512), nullable=False)
    platform: M[DevicePlatform] = mc(Enum(DevicePlatform), nullable=False)
    last_seen_at: M[datetime.datetime] = mc(DateTime(timezone=True), default=func.now())
