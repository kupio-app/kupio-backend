from pydantic import BaseModel, ConfigDict
import datetime
import uuid

from src.domains.users.schemas import UserPrivate


class LoginRequest(BaseModel):
    email: str
    password: str
    device_id: str


class RegisterRequest(LoginRequest):
    username: str


class RefreshRequest(BaseModel):
    refresh_token: str
    device_id: str


class TokensResponse(BaseModel):
    access_token: str
    refresh_token: str
    access_expires_at: int
    refresh_expires_at: int
    token_type: str = "bearer"


class MeResponse(BaseModel):
    user: UserPrivate


class SessionInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    device_id: str
    expires_at: datetime.datetime
    last_used_at: datetime.datetime
    is_revoked: bool


class SessionsResponse(BaseModel):
    sessions: list[SessionInfo]
