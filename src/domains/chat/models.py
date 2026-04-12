import uuid

from sqlalchemy import String, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import Mapped as M, mapped_column as mc, relationship

from src.core.database.base_model import Base, UUID
from src.core.database.mixins import SoftDeleteMixin


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        UniqueConstraint(
            "listing_id", "buyer_id", name="uq_conversation_listing_buyer"
        ),
    )

    id: M[UUID] = mc(primary_key=True, default=uuid.uuid4)
    listing_id: M[UUID] = mc(
        ForeignKey("listings.id", ondelete="CASCADE"), index=True, nullable=False
    )
    buyer_id: M[UUID] = mc(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    seller_id: M[UUID] = mc(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    last_message_preview: M[str | None] = mc(String(255), nullable=True)

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
