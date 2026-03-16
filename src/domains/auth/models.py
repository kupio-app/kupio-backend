import datetime
import uuid

from sqlalchemy import ForeignKey, String, func, DateTime
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
