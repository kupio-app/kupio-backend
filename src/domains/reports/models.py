import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped as M, mapped_column as mc, relationship

from src.core.database.base_model import Base, Int16, Int64, UUID
from .enums import ReportStatus

if TYPE_CHECKING:
    from src.domains.listings.models import Listing


_PENDING_REPORTS_CONDITION = text("status = 'PENDING'")


class ReportReason(Base):
    __tablename__ = "report_reasons"

    __table_args__ = (
        Index(
            "ix_report_reasons_active_display_order_id",
            "is_active",
            "display_order",
            "id",
        ),
    )

    id: M[Int64] = mc(primary_key=True, autoincrement=True)
    slug: M[str] = mc(String(100), unique=True, nullable=False)
    title: M[str] = mc(String(255), nullable=False)
    description: M[str | None] = mc(String(1000))
    display_order: M[Int16] = mc(default=0)
    is_active: M[bool] = mc(default=True)


class ListingReport(Base):
    __tablename__ = "listing_reports"

    __table_args__ = (
        Index("ix_listing_reports_status_created_id", "status", "created_at", "id"),
        Index("ix_listing_reports_seen_created_id", "seen_at", "created_at", "id"),
        Index("ix_listing_reports_listing_id", "listing_id"),
        Index("ix_listing_reports_reporter_id", "reporter_id"),
        Index(
            "uq_listing_reports_listing_reporter_pending",
            "listing_id",
            "reporter_id",
            unique=True,
            sqlite_where=_PENDING_REPORTS_CONDITION,
            postgresql_where=_PENDING_REPORTS_CONDITION,
        ),
    )

    id: M[Int64] = mc(primary_key=True, autoincrement=True)
    listing_id: M[UUID] = mc(
        ForeignKey("listings.id", ondelete="CASCADE"), nullable=False
    )
    reporter_id: M[UUID] = mc(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    reason_id: M[Int64] = mc(ForeignKey("report_reasons.id"), nullable=False)
    additional_info: M[str | None] = mc(String(2000))
    status: M[ReportStatus] = mc(Enum(ReportStatus), nullable=False)
    seen_at: M[datetime.datetime | None]
    seen_by_moderator_id: M[UUID | None] = mc(ForeignKey("users.id"))
    moderated_at: M[datetime.datetime | None]
    moderator_id: M[UUID | None] = mc(ForeignKey("users.id"))
    moderator_comment: M[str | None] = mc(String(2000))

    listing: M["Listing"] = relationship("Listing", lazy="joined")
    reason: M[ReportReason] = relationship("ReportReason", lazy="joined")
