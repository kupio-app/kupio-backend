import uuid
import datetime

from sqlalchemy import (
    String,
    Enum,
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
    func,
    and_,
)
from sqlalchemy.orm import Mapped as M, mapped_column as mc, relationship

from src.core.database.base_model import Base, UUID, Int64
from src.core.database.mixins import SoftDeleteMixin
from src.domains.images.models import Image

from .enums import UserRole, DevicePlatform


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
    balance: M[Int64] = mc(default=0)  # balance in cents
    avatar_image_id: M[UUID | None] = mc(ForeignKey("images.id", ondelete="SET NULL"))
    avatar_image: M[Image | None] = relationship(
        "Image",
        lazy="raise_on_sql",
        primaryjoin=lambda: and_(
            User.avatar_image_id == Image.id,
            Image.deleted_at.is_(None),
        ),
    )

    @property
    def display_name(self) -> str | None:
        parts = [p for p in (self.first_name, self.last_name) if p]
        return " ".join(parts) or None

    @property
    def needs_username(self) -> bool:
        return self.username is None

    @property
    def avatar_url(self) -> str | None:
        if self.avatar_image is None:
            return None

        return self.avatar_image.url


class DeviceToken(Base):
    __tablename__ = "device_tokens"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "platform", "token", name="uq_device_token_user_platform_token"
        ),
        Index("ix_device_tokens_user_id", "user_id"),
    )

    id: M[UUID] = mc(primary_key=True, default=uuid.uuid4)
    user_id: M[UUID] = mc(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token: M[str] = mc(String(512), nullable=False)
    platform: M[DevicePlatform] = mc(Enum(DevicePlatform), nullable=False)
    last_seen_at: M[datetime.datetime] = mc(DateTime(timezone=True), default=func.now())
