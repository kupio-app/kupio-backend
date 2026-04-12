import datetime
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.core.database.base_model import UUID
from src.core.utils.pydantic import NormalizedOptionalString
from src.domains.listings.enums import CurrencyEnum, ListingStatus

from .enums import ReportDecisionAction, ReportStatus

_SLUG_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def _validate_slug(v: str) -> str:
    if not _SLUG_RE.match(v):
        raise ValueError(
            "slug must start with a lowercase letter and contain only lowercase letters, digits, and underscores"
        )

    return v


class ReportReasonCreateRequest(BaseModel):
    slug: str = Field(max_length=100)
    title: str = Field(max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    display_order: int = Field(default=0, ge=0)
    is_active: bool = True

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        return _validate_slug(v)


class ReportReasonUpdateRequest(BaseModel):
    display_order: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


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


class ReportSellerSummary(BaseModel):
    id: UUID
    username: str | None
    display_name: str | None


class ReportListingSummary(BaseModel):
    id: UUID
    title: str
    price: int
    currency: CurrencyEnum
    status: ListingStatus
    primary_image_url: str | None


class ReportListingDetail(BaseModel):
    id: UUID
    title: str
    description: str
    price: int
    currency: CurrencyEnum
    status: ListingStatus
    primary_image_url: str | None


class CreatedListingReportResponse(BaseModel):
    id: int
    listing_id: UUID
    reason: ReportReasonSummary
    additional_info: str | None
    status: ReportStatus
    created_at: datetime.datetime
    updated_at: datetime.datetime | None


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


class ModerateReportRequest(BaseModel):
    action: ReportDecisionAction
    comment: NormalizedOptionalString = Field(default=None, max_length=2000)
