import uuid

from sqlalchemy import String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped as M, mapped_column as mc

from src.core.database.base_model import Base, UUID, Int64, Int16
from src.core.database.mixins import SoftDeleteMixin


class Image(Base, SoftDeleteMixin):
    __tablename__ = "images"

    id: M[UUID] = mc(primary_key=True, default=uuid.uuid4)
    s3_key: M[str] = mc(String(1024), unique=True)
    content_type: M[str] = mc(String(100))
    size_bytes: M[Int64]


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
    listing_id: M[UUID] = mc(ForeignKey("listings.id"), ondelete="CASCADE")
    image_id: M[UUID] = mc(ForeignKey("images.id"), ondelete="CASCADE")
    # 0 means it is the primary image (cover)
    sort_order: M[Int16]
