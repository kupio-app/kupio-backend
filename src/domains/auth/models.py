import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped as M, mapped_column as mc

from src.core.database.base_model import Base, UUID


class Session(Base):
    __tablename__ = "sessions"

    id: M[UUID] = mc(primary_key=True, default=uuid.uuid4)
    user_id: M[UUID] = mc(ForeignKey("users.id", ondelete="CASCADE"))
    token_hash: M[str] = mc(String(64), unique=True, index=True)
    device_id: M[str] = mc(String(255))
    expires_at: M[datetime.datetime] = mc(DateTime(timezone=True))
    last_used_at: M[datetime.datetime] = mc(DateTime(timezone=True), default=func.now)
    is_revoked: M[bool] = mc(default=False)


class OAuthIdentity(Base):
    __tablename__ = "oauth_identities"
    __table_args__ = (
        UniqueConstraint("provider", "provider_sub"),
        UniqueConstraint("provider", "user_id"),
    )

    id: M[UUID] = mc(primary_key=True, default=uuid.uuid4)
    user_id: M[UUID] = mc(ForeignKey("users.id", ondelete="CASCADE"))
    provider: M[str] = mc(String(50), index=True)
    provider_sub: M[str] = mc(String(255), index=True)
    last_login_at: M[datetime.datetime] = mc(DateTime(timezone=True), default=func.now)
