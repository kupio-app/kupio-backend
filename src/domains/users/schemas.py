import re
import uuid
import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_extra_types.phone_numbers import PhoneNumber

from .enums import UserRole, DevicePlatform


def validate_username_format(v: str) -> str:
    if not re.match(r"^[a-zA-Z0-9_-]+$", v):
        raise ValueError("Special characters are not allowed in username")

    return v


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    display_name: str | None


class UserPrivate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str | None
    display_name: str | None
    email: str
    role: UserRole
    needs_username: bool


class UpdateUserProfile(BaseModel):
    first_name: str | None = Field(None, min_length=2, max_length=100)
    last_name: str | None = Field(None, min_length=2, max_length=100)
    phone: PhoneNumber | None = None

    @field_validator("first_name", "last_name")
    @classmethod
    def name_valid(cls, v: str | None) -> str | None:
        if v is None:
            return v

        if not re.match(r"^[\w\s\-']+$", v, re.UNICODE):
            raise ValueError("No special characters allowed in names")

        return v.strip()


class SetUsernameRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: str) -> str:
        return validate_username_format(v)


class RegisterDeviceTokenRequest(BaseModel):
    token: str = Field(min_length=1, max_length=512)
    platform: DevicePlatform


class DeviceTokenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    platform: DevicePlatform
    last_seen_at: datetime.datetime
