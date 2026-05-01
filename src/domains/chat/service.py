import logging
from uuid import UUID

from streaq import StreaqError

from src.worker import send_fcm_push
from src.core.worker.schemas import FcmPushPayload
from src.core.database.repositories import Repositories
from src.core.database.uow import UoW
from src.core.utils.pagination import decode_cursor, encode_cursor
from src.domains.listings.models import Listing
from src.domains.users.models import User

from .enums import ConversationRole
from .exceptions import (
    CannotMessageOwnListingError,
    ConversationNotFoundError,
    MessageNotFoundError,
    MessageNotOwnedError,
    NotConversationParticipantError,
)
from .models import Conversation, Message
from .redis import ChatRedisManager
from .schemas import (
    ConversationResponse,
    ListConversationsResponse,
    ListMessagesResponse,
    MessageResponse,
    UnreadCountResponse,
)
from .utils import generate_message_preview


logger = logging.getLogger(__name__)


class ChatService:
    def __init__(
        self, repos: Repositories, uow: UoW, chat_redis: ChatRedisManager
    ) -> None:
        self.repos = repos
        self.uow = uow
        self.chat_redis = chat_redis

    async def get_or_create_conversation(
        self, current_user: User, listing: Listing, start_with: str | None
    ) -> ConversationResponse:
        if listing.user_id == current_user.id:
            raise CannotMessageOwnListingError()

        existing = await self.repos.conversations.get_by_listing_and_buyer(
            listing.id, current_user.id
        )
        if existing:
            row = await self.repos.conversations.get_with_unread_count(
                existing.id, current_user.id
            )
            conv, unread_count = row
        else:
            async with self.uow:
                conv = await self.repos.conversations.create(
                    listing_id=listing.id,
                    buyer_id=current_user.id,
                    seller_id=listing.user_id,
                )
            unread_count = 0

        if start_with is not None:
            logger.info("Starting conversation %s with starting message", conv.id)
            await self.send_message(current_user, conv.id, start_with)

        return self._conv_response(conv, unread_count)

    async def get_conversation(
        self, current_user: User, conversation_id: UUID
    ) -> ConversationResponse:
        row = await self.repos.conversations.get_with_unread_count(
            conversation_id, current_user.id
        )
        if row is None:
            raise ConversationNotFoundError()
        conv, unread_count = row
        if current_user.id not in (conv.buyer_id, conv.seller_id):
            raise NotConversationParticipantError()
        return self._conv_response(conv, unread_count)

    async def list_conversations(
        self,
        current_user: User,
        *,
        role: ConversationRole,
        limit: int,
        cursor: str | None,
    ) -> ListConversationsResponse:
        cursor_created_at, cursor_id = decode_cursor(cursor) if cursor else (None, None)

        seller_or_buyer = {role.value.lower() + "_id": current_user.id}
        rows = await self.repos.conversations.list_as(
            **seller_or_buyer,
            limit=limit,
            cursor_created_at=cursor_created_at,
            cursor_id=cursor_id,
        )
        next_cursor = (
            encode_cursor(rows[-1][0].created_at, rows[-1][0].id)
            if len(rows) == limit
            else None
        )
        return ListConversationsResponse(
            conversations=[self._conv_response(conv, unread) for conv, unread in rows],
            next_cursor=next_cursor,
        )

    async def get_total_unread_count(self, current_user: User) -> UnreadCountResponse:
        count = await self.repos.conversations.get_total_unread_count(current_user.id)
        return UnreadCountResponse(unread_count=count)

    def _conv_response(
        self, conv: Conversation, unread_count: int
    ) -> ConversationResponse:
        return ConversationResponse(
            id=conv.id,
            listing_id=conv.listing_id,
            buyer_id=conv.buyer_id,
            seller_id=conv.seller_id,
            created_at=conv.created_at,
            last_message_preview=conv.last_message_preview,
            unread_count=unread_count,
        )

    async def _get_participant_conversation(
        self, current_user: User, conversation_id: UUID
    ) -> Conversation:
        conv = await self.repos.conversations.get_by_id(conversation_id)
        if conv is None:
            raise ConversationNotFoundError()
        if current_user.id not in (conv.buyer_id, conv.seller_id):
            raise NotConversationParticipantError()
        return conv

    async def send_message(
        self, current_user: User, conversation_id: UUID, body: str
    ) -> Message:
        conv = await self._get_participant_conversation(current_user, conversation_id)

        async with self.uow:
            msg = await self.repos.messages.create(
                conversation_id=conversation_id,
                sender_id=current_user.id,
                body=body,
            )
            await self.repos.conversations.update_message_preview(
                conversation_id=conversation_id, preview=generate_message_preview(msg)
            )

        await self.chat_redis.publish_message(msg)
        await self._maybe_enqueue_push(conv, msg, current_user.id)
        return msg

    async def delete_message(
        self, current_user: User, conversation_id: UUID, message_id: UUID
    ) -> None:
        await self._get_participant_conversation(current_user, conversation_id)

        msg = await self.repos.messages.get_by_id_in_conversation(
            message_id, conversation_id
        )
        if msg is None:
            raise MessageNotFoundError()
        if msg.sender_id != current_user.id:
            raise MessageNotOwnedError()

        async with self.uow:
            await self.repos.messages.soft_delete(message_id)

        await self.chat_redis.publish_deletion(conversation_id, message_id)

    async def list_messages(
        self,
        current_user: User,
        conversation_id: UUID,
        *,
        limit: int,
        cursor: str | None,
    ) -> ListMessagesResponse:
        await self._get_participant_conversation(current_user, conversation_id)
        async with self.uow:
            await self.repos.conversations.update_last_read_at(
                conversation_id, current_user.id
            )

        await self.chat_redis.publish_read(conversation_id, current_user.id)
        cursor_created_at, cursor_id = decode_cursor(cursor) if cursor else (None, None)
        msgs = await self.repos.messages.list_with_deleted(
            conversation_id,
            limit=limit,
            cursor_created_at=cursor_created_at,
            cursor_id=cursor_id,
        )
        next_cursor = (
            encode_cursor(msgs[-1].created_at, msgs[-1].id)
            if len(msgs) == limit
            else None
        )
        return ListMessagesResponse(
            messages=[MessageResponse.model_validate(m) for m in msgs],
            next_cursor=next_cursor,
        )

    async def _maybe_enqueue_push(
        self, conv: Conversation, msg: Message, sender_id: UUID
    ) -> None:
        recipient_id = conv.seller_id if sender_id == conv.buyer_id else conv.buyer_id
        if not await self.chat_redis.is_online(conv.id, recipient_id):
            try:
                await send_fcm_push.enqueue(
                    str(recipient_id),
                    FcmPushPayload(
                        title="New message",
                        body=generate_message_preview(msg),
                        type="chat_message",
                        data={"conversation_id": str(conv.id)},
                    ),
                )
            except StreaqError as e:
                logger.error(e)
