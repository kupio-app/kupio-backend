import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.core.database.base_model import UUID
from src.core.utils.pydantic import NormalizedOptionalString, validate_slug
from src.domains.images.models import ListingImage
from src.domains.listings.enums import CurrencyEnum, ListingStatus

from .enums import ReportDecisionAction, ReportStatus

if TYPE_CHECKING:
    from src.domains.listings.models import Listing
    from src.domains.reports.models import ListingReport, ReportReason


class ReportReasonCreateRequest(BaseModel):
    slug: str = Field(max_length=100)
    title: str = Field(max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    display_order: int = Field(default=0, ge=0)
    is_active: bool = True

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        return validate_slug(v)


class ReportReasonUpdateRequest(BaseModel):
    display_order: int | None = Field(default=None, ge=0)
    is_active: bool | None = None

    @field_validator("display_order", "is_active")
    @classmethod
    def reject_explicit_null(cls, v):
        if v is None:
            raise ValueError("Field may be omitted, but cannot be null")
        return v


class ReportReasonResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    title: str
    description: str | None
    display_order: int
    is_active: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime | None


class CreateListingReportRequest(BaseModel):
    reason_id: int
    additional_info: NormalizedOptionalString = Field(default=None, max_length=2000)


class ReportReasonSummary(BaseModel):
    id: int
    slug: str
    title: str
    description: str | None

    @classmethod
    def build_from(cls, reason: "ReportReason") -> "ReportReasonSummary":
        return cls(
            id=reason.id,
            slug=reason.slug,
            title=reason.title,
            description=reason.description,
        )


class ReportSellerSummary(BaseModel):
    id: UUID
    username: str | None
    display_name: str | None

    @classmethod
    def build_from(cls, listing: "Listing") -> "ReportSellerSummary":
        return cls(
            id=listing.user.id,
            username=listing.user.username,
            display_name=listing.user.display_name,
        )


class ReportListingSummary(BaseModel):
    id: UUID
    title: str
    price: int
    currency: CurrencyEnum
    status: ListingStatus
    primary_image_url: str | None

    @classmethod
    def build_from(cls, listing: "Listing") -> "ReportListingSummary":
        return cls(
            id=listing.id,
            title=listing.title,
            price=listing.price,
            currency=listing.currency,
            status=listing.status,
            primary_image_url=_build_primary_image_url(listing),
        )


class ReportListingDetail(BaseModel):
    id: UUID
    title: str
    description: str
    price: int
    currency: CurrencyEnum
    status: ListingStatus
    primary_image_url: str | None

    @classmethod
    def build_from(cls, listing: "Listing") -> "ReportListingDetail":
        return cls(
            id=listing.id,
            title=listing.title,
            description=listing.description,
            price=listing.price,
            currency=listing.currency,
            status=listing.status,
            primary_image_url=_build_primary_image_url(listing),
        )


class CreatedListingReportResponse(BaseModel):
    id: int
    listing_id: UUID
    reason: ReportReasonSummary
    additional_info: str | None
    status: ReportStatus
    created_at: datetime.datetime
    updated_at: datetime.datetime | None

    @classmethod
    def build_from(cls, report: "ListingReport") -> "CreatedListingReportResponse":
        return cls(
            id=report.id,
            listing_id=report.listing_id,
            reason=ReportReasonSummary.build_from(report.reason),
            additional_info=report.additional_info,
            status=report.status,
            created_at=report.created_at,
            updated_at=report.updated_at,
        )


class ReportsDashboardStats(BaseModel):
    new_today: int
    no_action: int
    unseen: int


class ReportListItem(BaseModel):
    id: int
    status: ReportStatus
    created_at: datetime.datetime
    seen: bool
    reason: ReportReasonSummary
    additional_info_preview: str | None
    listing: ReportListingSummary
    seller: ReportSellerSummary

    @classmethod
    def build_from(
        cls,
        report: "ListingReport",
        *,
        additional_info_preview_length: int,
    ) -> "ReportListItem":
        return cls(
            id=report.id,
            status=report.status,
            created_at=report.created_at,
            seen=report.seen_at is not None,
            reason=ReportReasonSummary.build_from(report.reason),
            additional_info_preview=_build_additional_info_preview(
                report.additional_info,
                max_length=additional_info_preview_length,
            ),
            listing=ReportListingSummary.build_from(report.listing),
            seller=ReportSellerSummary.build_from(report.listing),
        )


class ListReportsResponse(BaseModel):
    stats: ReportsDashboardStats
    reports: list[ReportListItem]
    next_cursor: str | None


class ReportDetailResponse(BaseModel):
    id: int
    status: ReportStatus
    created_at: datetime.datetime
    updated_at: datetime.datetime | None
    additional_info: str | None
    reason: ReportReasonSummary
    listing: ReportListingDetail
    seller: ReportSellerSummary
    seen_at: datetime.datetime | None
    seen_by_moderator_id: UUID | None
    moderated_at: datetime.datetime | None
    moderator_id: UUID | None
    moderator_comment: str | None

    @classmethod
    def build_from(cls, report: "ListingReport") -> "ReportDetailResponse":
        return cls(
            id=report.id,
            status=report.status,
            created_at=report.created_at,
            updated_at=report.updated_at,
            additional_info=report.additional_info,
            reason=ReportReasonSummary.build_from(report.reason),
            listing=ReportListingDetail.build_from(report.listing),
            seller=ReportSellerSummary.build_from(report.listing),
            seen_at=report.seen_at,
            seen_by_moderator_id=report.seen_by_moderator_id,
            moderated_at=report.moderated_at,
            moderator_id=report.moderator_id,
            moderator_comment=report.moderator_comment,
        )


class ModerateReportRequest(BaseModel):
    action: ReportDecisionAction
    comment: NormalizedOptionalString = Field(default=None, max_length=2000)


def _build_additional_info_preview(
    value: str | None,
    *,
    max_length: int,
) -> str | None:
    if value is None or len(value) <= max_length:
        return value

    return value[:max_length].rstrip() + "..."


def _build_primary_image_url(listing: "Listing") -> str | None:
    for listing_image in listing.images:
        if isinstance(listing_image, ListingImage) and listing_image.image is not None:
            return listing_image.image.url
    return None
