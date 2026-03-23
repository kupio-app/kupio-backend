import re
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_extra_types.phone_numbers import PhoneNumber

from src.domains.users.enums import UserRole


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    display_name: str | None


class UserPrivate(UserPublic):
    email: str
    role: UserRole


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
