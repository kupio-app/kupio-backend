import uuid

from sqlalchemy import String, ForeignKey, UniqueConstraint, and_
from sqlalchemy.orm import Mapped as M, mapped_column as mc, relationship
from typing import TYPE_CHECKING

from src.core.config import get_config
from src.core.database.base_model import Base, UUID, Int64, Int16
from src.core.database.mixins import SoftDeleteMixin

if TYPE_CHECKING:
    from src.domains.listings.models import Listing


class Image(Base, SoftDeleteMixin):
    __tablename__ = "images"

    id: M[UUID] = mc(primary_key=True, default=uuid.uuid4)
    s3_key: M[str] = mc(String(1024), unique=True)
    content_type: M[str] = mc(String(100))
    size_bytes: M[Int64]

    @property
    def url(self) -> str:
        return get_config().s3.build_public_url(self.s3_key)


class ListingImage(Base):
    __tablename__ = "listing_images"
    __table_args__ = (
        UniqueConstraint(
            "listing_id", "image_id", name="uq_listing_images_listing_id_image_id"
        ),
        UniqueConstraint(
            "listing_id", "sort_order", name="uq_listing_images_listing_id_sort_order"
        ),
    )

    id: M[UUID] = mc(primary_key=True, default=uuid.uuid4)
    listing_id: M[UUID] = mc(ForeignKey("listings.id", ondelete="CASCADE"))
    image_id: M[UUID] = mc(ForeignKey("images.id", ondelete="CASCADE"))
    listing: M["Listing"] = relationship("Listing", back_populates="images")
    image: M[Image | None] = relationship(
        "Image",
        lazy="joined",
        primaryjoin=lambda: and_(
            ListingImage.image_id == Image.id,
            Image.deleted_at.is_(None),
        ),
    )
    # 0 means it is the primary image (cover)
    sort_order: M[Int16]

    @property
    def url(self) -> str:
        return self.image.url
