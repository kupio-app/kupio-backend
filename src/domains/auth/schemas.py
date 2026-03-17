from pydantic import BaseModel

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
    token_type: str = "bearer"


class MeResponse(BaseModel):
    user: UserPrivate
