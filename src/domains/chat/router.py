from uuid import UUID
from fastapi import APIRouter, Depends, status, WebSocket, Query

from src.core.dependencies import get_current_user
from src.core.utils.pagination import PaginationParams
from src.domains.listings.service import ListingsService
from src.domains.listings.dependencies import get_listings_service
from src.domains.users.models import User

from .dependencies import get_chat_service
from .enums import ConversationRole
from .service import ChatService
from .schemas import (
    ConversationResponse,
    ListConversationsResponse,
    ListMessagesResponse,
    MessageResponse,
    SendMessageRequest,
)
from .ws.handler import handle_chat_ws

router = APIRouter()


@router.post(
    "/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_conversation(
    listing_id: UUID,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
    listings_service: ListingsService = Depends(get_listings_service),
):
    listing = await listings_service.get_listing(listing_id)
    conv = await service.get_or_create_conversation(current_user, listing)
    return ConversationResponse.model_validate(conv)


@router.get("/conversations", response_model=ListConversationsResponse)
async def list_buyer_conversations(
    role: ConversationRole,
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    return await service.list_conversations(
        current_user, role=role, limit=pagination.limit, cursor=pagination.cursor
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    return await service.get_conversation(current_user, conversation_id)


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=ListMessagesResponse,
)
async def list_messages(
    conversation_id: UUID,
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    return await service.list_messages(
        current_user,
        conversation_id,
        limit=pagination.limit,
        cursor=pagination.cursor,
    )


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_message(
    conversation_id: UUID,
    payload: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    return await service.send_message(current_user, conversation_id, payload.body)


@router.delete(
    "/conversations/{conversation_id}/messages/{message_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_message(
    conversation_id: UUID,
    message_id: UUID,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    await service.delete_message(current_user, conversation_id, message_id)


@router.websocket("/conversations/{conversation_id}/ws")
async def chat_ws(
    websocket: WebSocket,
    conversation_id: UUID,
    last_message_id: UUID | None = Query(None),
):
    await handle_chat_ws(
        websocket=websocket,
        conversation_id=conversation_id,
        last_message_id=last_message_id,
    )
