import uuid

from sqlalchemy import String, Enum
from sqlalchemy.orm import Mapped as M, mapped_column as mc

from src.core.database.base_model import Base, UUID
from src.core.database.mixins import SoftDeleteMixin
from src.domains.users.enums import UserRole


class User(Base, SoftDeleteMixin):
    __tablename__ = "users"

    id: M[UUID] = mc(primary_key=True, default=uuid.uuid4)
    username: M[str] = mc(String(50), unique=True, index=True)
    email: M[str] = mc(String(255), unique=True, index=True)
    phone: M[str | None] = mc(String(20), unique=True, index=True)
    display_name: M[str | None] = mc(String(100))
    password_hash: M[str] = mc(String(512))
    role: M[UserRole] = mc(Enum(UserRole), default=UserRole.USER)
