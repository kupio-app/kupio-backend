from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class WsErrorMessage(BaseModel):
    type: Literal["error"] = "error"
    code: str


class WsAuthOkMessage(BaseModel):
    type: Literal["auth_ok"] = "auth_ok"
    conversation_id: UUID


class WsPongMessage(BaseModel):
    type: Literal["pong"] = "pong"


class WsTypingMessage(BaseModel):
    type: Literal["typing"] = "typing"
    user_id: UUID


class WsMessagesReadMessage(BaseModel):
    type: Literal["messages_read"] = "messages_read"
    user_id: UUID
