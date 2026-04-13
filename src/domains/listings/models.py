import uuid
from typing import TYPE_CHECKING

from sqlalchemy import String, Enum, ForeignKey, Index
from sqlalchemy.orm import Mapped as M, mapped_column as mc, relationship

from src.core.database.base_model import Base, UUID, Int64, JSONDict
from src.core.database.mixins import SoftDeleteMixin
from src.domains.images.models import ListingImage
from src.domains.listings.enums import ListingStatus, CurrencyEnum

if TYPE_CHECKING:
    from src.domains.users.models import User
    from src.domains.categories.models import Category


class Listing(Base, SoftDeleteMixin):
    __tablename__ = "listings"

    __table_args__ = (
        Index("ix_listings_custom_filters", "custom_filters", postgresql_using="gin"),
    )

    id: M[UUID] = mc(primary_key=True, default=uuid.uuid4)
    user_id: M[UUID] = mc(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user: M["User"] = relationship("User", lazy="joined")
    category_id: M[Int64] = mc(ForeignKey("categories.id"), nullable=False)
    category: M["Category"] = relationship("Category", lazy="raise_on_sql")
    images: M[list[ListingImage]] = relationship(
        "ListingImage",
        lazy="raise_on_sql",
        order_by=lambda: ListingImage.sort_order,
        back_populates="listing",
    )
    title: M[str] = mc(String(255))
    description: M[str]
    price: M[Int64]
    is_free: M[bool] = mc(default=False)
    is_tradable: M[bool] = mc(default=False)
    currency: M[CurrencyEnum] = mc(Enum(CurrencyEnum))
    status: M[ListingStatus] = mc(Enum(ListingStatus))
    custom_filters: M[JSONDict | None] = mc(default=None)


class ListingView(Base):
    __tablename__ = "listing_views"

    __table_args__ = (
        Index("ix_listing_views_listing_created", "listing_id", "created_at"),
    )

    id: M[UUID] = mc(primary_key=True, default=uuid.uuid4)
    listing_id: M[UUID] = mc(
        ForeignKey("listings.id", ondelete="CASCADE"), nullable=False
    )
    viewer_user_id: M[UUID | None] = mc(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    listing: M["Listing"] = relationship("Listing", lazy="joined")
    viewer: M["User | None"] = relationship("User", lazy="joined")
