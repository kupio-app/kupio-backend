import re

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
import datetime
import uuid

from src.domains.users.schemas import UserPrivate


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    device_id: str


class RegisterRequest(LoginRequest):
    username: str = Field(min_length=3, max_length=50)
    password: str

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("Special characters are not allowed in username")

        return v


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
