import uuid

from pydantic import BaseModel, ConfigDict

from src.domains.users.enums import UserRole


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    display_name: str | None


class UserPrivate(UserPublic):
    email: str
    role: UserRole
