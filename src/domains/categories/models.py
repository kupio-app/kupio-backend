from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped as M, mapped_column as mc, relationship

from src.core.database.base_model import Base, Int64, Int16
from src.core.database.mixins import SoftDeleteMixin


class Category(Base, SoftDeleteMixin):
    __tablename__ = "categories"

    id: M[Int64] = mc(primary_key=True, autoincrement=True)
    name: M[str] = mc(String(255), unique=True, nullable=False)
    depth: M[Int16] = mc(default=0)
    parent_id: M[Int64 | None] = mc(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    parent: M["Category"] = relationship(
        "Category",
        remote_side=[id],
        lazy="joined",
    )
