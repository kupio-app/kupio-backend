import datetime
import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from src.domains.users.schemas import validate_username_format


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    device_id: str


class RegisterRequest(LoginRequest):
    username: str = Field(min_length=3, max_length=50)

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: str) -> str:
        return validate_username_format(v)


class RefreshRequest(BaseModel):
    refresh_token: str
    device_id: str


class TokensResponse(BaseModel):
    access_token: str
    refresh_token: str
    access_expires_at: int
    refresh_expires_at: int
    token_type: str = "bearer"
    needs_username: bool = False


class SessionInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    device_id: str
    expires_at: datetime.datetime
    last_used_at: datetime.datetime
    is_revoked: bool


class SessionsResponse(BaseModel):
    sessions: list[SessionInfo]


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)
    device_id: str


class GoogleLoginRequest(BaseModel):
    id_token: str = Field(min_length=1)
    device_id: str


class SetPasswordRequest(BaseModel):
    new_password: str = Field(min_length=8, max_length=128)
    device_id: str
