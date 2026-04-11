import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select, and_, or_, ColumnElement

from src.core.database.base_repository import BaseRepository
from src.domains.chat.models import Conversation, Message


class ConversationsRepository(BaseRepository):
    async def get_by_id(self, conversation_id: UUID) -> Conversation | None:
        return await self._get(Conversation, Conversation.id == conversation_id)

    async def get_by_listing_and_buyer(
        self, listing_id: UUID, buyer_id: UUID
    ) -> Conversation | None:
        return await self._get(
            Conversation,
            Conversation.listing_id == listing_id,
            Conversation.buyer_id == buyer_id,
        )

    async def create(
        self, *, listing_id: UUID, buyer_id: UUID, seller_id: UUID
    ) -> Conversation:
        return await self._add(
            Conversation,
            listing_id=listing_id,
            buyer_id=buyer_id,
            seller_id=seller_id,
        )

    async def list_as(
        self,
        *,
        seller_id: UUID = None,
        buyer_id: UUID = None,
        limit: int,
        cursor_created_at: datetime.datetime | None = None,
        cursor_id: UUID | None = None,
    ) -> list[Conversation]:
        if not any([seller_id, buyer_id]):
            raise ValueError("seller_id, buyer_id must be provided")

        conditions: list[ColumnElement[Any]] = []
        if seller_id is not None:
            conditions.append(Conversation.seller_id == seller_id)
        else:
            conditions.append(Conversation.buyer_id == buyer_id)

        if cursor_created_at and cursor_id:
            conditions.append(
                or_(
                    Conversation.created_at < cursor_created_at,
                    and_(
                        Conversation.created_at == cursor_created_at,
                        Conversation.id < cursor_id,
                    ),
                )
            )
        stmt = (
            select(Conversation)
            .where(*conditions)
            .order_by(Conversation.created_at.desc(), Conversation.id.desc())
            .limit(limit)
        )
        return await self._scalars_all(stmt)


class MessagesRepository(BaseRepository):
    async def create(
        self, *, conversation_id: UUID, sender_id: UUID, body: str
    ) -> Message:
        return await self._add(
            Message,
            conversation_id=conversation_id,
            sender_id=sender_id,
            body=body,
        )

    async def get_by_id_in_conversation(
        self, message_id: UUID, conversation_id: UUID
    ) -> Message | None:
        # Bypass _get() — we need to fetch soft-deleted messages too
        # (to check ownership before performing delete)
        stmt = select(Message).where(
            Message.id == message_id,
            Message.conversation_id == conversation_id,
        )
        return await self.session.scalar(stmt)

    async def list_with_deleted(
        self,
        conversation_id: UUID,
        *,
        limit: int,
        cursor_created_at: datetime.datetime | None = None,
        cursor_id: UUID | None = None,
    ) -> list[Message]:
        # Deliberately no deleted_at.is_(None) — deleted messages show as body=null
        conditions: list = [Message.conversation_id == conversation_id]
        if cursor_created_at and cursor_id:
            conditions.append(
                or_(
                    Message.created_at < cursor_created_at,
                    and_(
                        Message.created_at == cursor_created_at,
                        Message.id < cursor_id,
                    ),
                )
            )
        stmt = (
            select(Message)
            .where(*conditions)
            .order_by(Message.created_at.desc(), Message.id.desc())
            .limit(limit)
        )
        return await self._scalars_all(stmt)

    async def soft_delete(self, message_id: UUID) -> bool:
        return await self._soft_delete(Message, Message.id == message_id)

    async def get_messages_after(
        self, conversation_id: UUID, after_message_id: UUID
    ) -> list[Message]:
        """Used on reconnect: fetch non-deleted messages sent after the given message."""
        anchor_stmt = select(Message.created_at).where(Message.id == after_message_id)
        anchor_ts = await self.session.scalar(anchor_stmt)
        if anchor_ts is None:
            return []

        stmt = (
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.deleted_at.is_(None),
                or_(
                    Message.created_at > anchor_ts,
                    and_(
                        Message.created_at == anchor_ts,
                        Message.id > after_message_id,
                    ),
                ),
            )
            .order_by(Message.created_at.asc(), Message.id.asc())
            .limit(200)
        )
        return await self._scalars_all(stmt)
