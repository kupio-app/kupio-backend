import datetime

from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, computed_field


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    listing_id: UUID
    buyer_id: UUID
    seller_id: UUID
    created_at: datetime.datetime


class ListConversationsResponse(BaseModel):
    conversations: list[ConversationResponse]
    next_cursor: str | None


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    sender_id: UUID
    body: str | None = Field(exclude=True)
    is_deleted: bool
    created_at: datetime.datetime

    @computed_field
    def content(self) -> str | None:
        return None if self.is_deleted else self.body


class ListMessagesResponse(BaseModel):
    messages: list[MessageResponse]
    next_cursor: str | None


class SendMessageRequest(BaseModel):
    body: str = Field(min_length=1, max_length=4000)
