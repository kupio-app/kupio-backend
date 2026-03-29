from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped as M, mapped_column as mc, relationship

from src.core.database.base_model import Base, UUID

if TYPE_CHECKING:
    from src.domains.listings.models import Listing
    from src.domains.users.models import User


class ListingFavourite(Base):
    __tablename__ = "listing_favourites"

    user_id: M[UUID] = mc(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    listing_id: M[UUID] = mc(
        ForeignKey("listings.id", ondelete="CASCADE"),
        primary_key=True,
    )

    user: M["User"] = relationship("User", lazy="joined")
    listing: M["Listing"] = relationship("Listing", lazy="joined")
