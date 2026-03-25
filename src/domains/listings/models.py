import uuid
from typing import TYPE_CHECKING

from sqlalchemy import String, Enum, ForeignKey
from sqlalchemy.orm import Mapped as M, mapped_column as mc, relationship

from src.core.database.base_model import Base, UUID, Int64
from src.core.database.mixins import SoftDeleteMixin
from src.domains.listings.enums import ListingStatus, CurrencyEnum

if TYPE_CHECKING:
    from src.domains.users.models import User
    from src.domains.categories.models import Category


class Listing(Base, SoftDeleteMixin):
    __tablename__ = "listings"

    id: M[UUID] = mc(primary_key=True, default=uuid.uuid4)
    user_id: M[UUID] = mc(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user: M["User"] = relationship("User", lazy="joined")
    category_id: M[Int64] = mc(ForeignKey("categories.id"), nullable=False)
    category: M["Category"] = relationship("Category", lazy="joined")
    title: M[str] = mc(String(255))
    description: M[str]
    price: M[Int64]
    is_free: M[bool] = mc(default=False)
    is_tradable: M[bool] = mc(default=False)
    currency: M[CurrencyEnum] = mc(Enum(CurrencyEnum))
    status: M[ListingStatus] = mc(Enum(ListingStatus))
