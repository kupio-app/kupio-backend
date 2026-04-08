import uuid

from sqlalchemy import String, Enum, ForeignKey
from sqlalchemy.orm import Mapped as M, mapped_column as mc

from src.core.database.base_model import Base, UUID
from src.core.database.mixins import SoftDeleteMixin
from src.domains.users.enums import UserRole


class User(Base, SoftDeleteMixin):
    __tablename__ = "users"

    id: M[UUID] = mc(primary_key=True, default=uuid.uuid4)
    username: M[str | None] = mc(String(50), unique=True, index=True)
    email: M[str] = mc(String(255), unique=True, index=True)
    phone: M[str | None] = mc(String(20), unique=True, index=True)
    first_name: M[str | None] = mc(String(100))
    last_name: M[str | None] = mc(String(100))
    password_hash: M[str | None] = mc(String(512))
    role: M[UserRole] = mc(Enum(UserRole), default=UserRole.USER)
    avatar_image_id: M[UUID | None] = mc(ForeignKey("images.id"), ondelete="SET NULL")

    @property
    def display_name(self) -> str | None:
        parts = [p for p in (self.first_name, self.last_name) if p]
        return " ".join(parts) or None

    @property
    def needs_username(self) -> bool:
        return self.username is None
