from uuid import UUID

from redis.asyncio import Redis

from src.core.database.repositories import Repositories
from src.core.database.uow import UoW
from src.core.utils.pagination import decode_cursor, encode_cursor
from src.domains.chat.enums import ConversationRole
from src.domains.chat.exceptions import (
    CannotMessageOwnListingError,
    ConversationNotFoundError,
    MessageNotFoundError,
    MessageNotOwnedError,
    NotConversationParticipantError,
)
from src.domains.chat.models import Conversation, Message
from src.domains.chat.schemas import (
    ConversationResponse,
    DeviceTokenResponse,
    ListConversationsResponse,
    ListMessagesResponse,
    MessageResponse,
    RegisterDeviceTokenRequest,
)
from src.domains.listings.models import Listing
from src.domains.users.models import User


class ChatService:
    def __init__(self, repos: Repositories, uow: UoW, redis: Redis) -> None:
        self.repos = repos
        self.uow = uow
        self.redis = redis

    async def get_or_create_conversation(
        self, current_user: User, listing: Listing
    ) -> Conversation:
        if listing.user_id == current_user.id:
            raise CannotMessageOwnListingError()

        existing = await self.repos.conversations.get_by_listing_and_buyer(
            listing.id, current_user.id
        )
        if existing:
            return existing

        async with self.uow:
            return await self.repos.conversations.create(
                listing_id=listing.id,
                buyer_id=current_user.id,
                seller_id=listing.user_id,
            )

    async def get_conversation(
        self, current_user: User, conversation_id: UUID
    ) -> Conversation:
        conv = await self.repos.conversations.get_by_id(conversation_id)
        if conv is None:
            raise ConversationNotFoundError()

        if current_user.id not in (conv.buyer_id, conv.seller_id):
            raise NotConversationParticipantError()

        return conv

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
        convs = await self.repos.conversations.list_as(
            **seller_or_buyer,
            limit=limit,
            cursor_created_at=cursor_created_at,
            cursor_id=cursor_id,
        )
        next_cursor = (
            encode_cursor(convs[-1].created_at, convs[-1].id)
            if len(convs) == limit
            else None
        )
        return ListConversationsResponse(
            conversations=[ConversationResponse.model_validate(c) for c in convs],
            next_cursor=next_cursor,
        )

    async def send_message(
        self, current_user: User, conversation_id: UUID, body: str
    ) -> Message:
        async with self.uow:
            return await self.repos.messages.create(
                conversation_id=conversation_id,
                sender_id=current_user.id,
                body=body,
            )

    async def delete_message(
        self, current_user: User, conversation_id: UUID, message_id: UUID
    ) -> None:
        await self.get_conversation(current_user, conversation_id)

        msg = await self.repos.messages.get_by_id_in_conversation(
            message_id, conversation_id
        )
        if msg is None:
            raise MessageNotFoundError()
        if msg.sender_id != current_user.id:
            raise MessageNotOwnedError()

        async with self.uow:
            await self.repos.messages.soft_delete(message_id)

    async def list_messages(
        self,
        current_user: User,
        conversation_id: UUID,
        *,
        limit: int,
        cursor: str | None,
    ) -> ListMessagesResponse:
        await self.get_conversation(current_user, conversation_id)
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


class DeviceTokenService:
    def __init__(self, repos: Repositories, uow: UoW) -> None:
        self.repos = repos
        self.uow = uow

    async def register_token(
        self, current_user: User, req: RegisterDeviceTokenRequest
    ) -> DeviceTokenResponse:
        async with self.uow:
            token = await self.repos.device_tokens.upsert(
                user_id=current_user.id,
                token=req.token,
                platform=req.platform,
            )
        return DeviceTokenResponse.model_validate(token)
