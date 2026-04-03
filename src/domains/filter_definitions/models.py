from typing import TYPE_CHECKING

from sqlalchemy import String, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped as M, mapped_column as mc, relationship

from src.core.database.base_model import Base, Int64, Int16, JSONDict
from .enums import FilterType

if TYPE_CHECKING:
    from src.domains.categories.models import Category


class FilterDefinition(Base):
    __tablename__ = "filter_definitions"

    __table_args__ = (
        UniqueConstraint(
            "category_id", "slug", name="uq_filter_definitions_category_slug"
        ),
        UniqueConstraint(
            "category_id",
            "display_order",
            name="uq_filter_definitions_category_display_order",
        ),
    )

    id: M[Int64] = mc(primary_key=True, autoincrement=True)
    category_id: M[Int64] = mc(
        ForeignKey("categories.id", ondelete="CASCADE"), nullable=False
    )
    category: M["Category"] = relationship("Category", lazy="joined")
    slug: M[str] = mc(String(100), nullable=False)
    label: M[str] = mc(String(255), nullable=False)
    filter_type: M[FilterType] = mc(Enum(FilterType), nullable=False)
    # SELECT: {"values": ["8 GB", "16 GB", "32 GB"]}
    # RANGE:  {"min": 0, "max": 128}
    # other filter types: unused (leave null)
    options: M[JSONDict | None]
    is_required: M[bool] = mc(default=False)
    display_order: M[Int16] = mc(default=0)
