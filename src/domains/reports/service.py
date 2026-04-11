import base64
import datetime
import json

from sqlalchemy.exc import IntegrityError

from src.domains.listings.models import Listing
from src.domains.users.models import User
from src.domains.images.models import ListingImage
from src.domains.reports.exceptions import (
    CannotReportOwnListingError,
    CustomReasonDetailsRequiredError,
    DuplicatePendingListingReportError,
    DuplicateReportReasonSlugError,
    ListingReportAlreadyResolvedError,
    ListingReportNotFoundError,
    OtherReasonCannotBeDeactivatedError,
    ReportReasonInactiveError,
    ReportReasonNotFoundError,
    ReservedOtherReasonSlugError,
)
from src.domains.reports.models import ListingReport, ReportReason
from src.domains.reports.schemas import (
    CreatedListingReportResponse,
    ListReportsResponse,
    ModerateReportRequest,
    ReportDetailResponse,
    ReportListingDetail,
    ReportListItem,
    ReportListingSummary,
    ReportReasonSummary,
    ReportReasonCreateRequest,
    ReportReasonUpdateRequest,
    ReportSellerSummary,
    ReportsDashboardStats,
    CreateListingReportRequest,
)
from src.core.database.repositories import Repositories
from src.core.database.uow import UoW
from .enums import ReportDecisionAction, ReportSeenFilter, ReportStatus
from .repository import ReportReasonsRepository, ReportsRepository

OTHER_REPORT_REASON_SLUG = "other"
ADDITIONAL_INFO_PREVIEW_LENGTH = 120


class ReportsService:
    def __init__(self, repos: Repositories, uow: UoW) -> None:
        self.repos = repos
        self.uow = uow
        self.report_reasons_repo: ReportReasonsRepository = repos.report_reasons
        self.reports_repo: ReportsRepository = repos.reports

    async def list_active_reasons(self) -> list[ReportReason]:
        return await self.report_reasons_repo.list_all()

    async def list_all_reasons(self) -> list[ReportReason]:
        return await self.report_reasons_repo.list_all(include_inactive=True)

    async def get_reason(self, reason_id: int) -> ReportReason:
        if (reason := await self.report_reasons_repo.get_by_id(reason_id)) is None:
            raise ReportReasonNotFoundError()
        return reason

    async def get_report(self, report_id: int) -> ListingReport:
        if (report := await self.reports_repo.get_by_id(report_id)) is None:
            raise ListingReportNotFoundError()
        return report

    async def create_reason(
        self,
        reason_data: ReportReasonCreateRequest,
    ) -> ReportReason:
        if reason_data.slug == OTHER_REPORT_REASON_SLUG:
            raise ReservedOtherReasonSlugError()

        if await self.report_reasons_repo.get_by_slug(reason_data.slug) is not None:
            raise DuplicateReportReasonSlugError()

        try:
            async with self.uow:
                return await self.report_reasons_repo.create(**reason_data.model_dump())
        except IntegrityError as exc:
            if await self.report_reasons_repo.get_by_slug(reason_data.slug) is not None:
                raise DuplicateReportReasonSlugError() from exc
            raise

    async def update_reason(
        self,
        reason: ReportReason,
        reason_data: ReportReasonUpdateRequest,
    ) -> ReportReason:
        updates = reason_data.model_dump(exclude_none=True)
        if not updates:
            return reason

        if (
            reason.slug == OTHER_REPORT_REASON_SLUG
            and updates.get("is_active") is False
        ):
            raise OtherReasonCannotBeDeactivatedError()

        async with self.uow:
            return await self.report_reasons_repo.update_by_id(reason.id, **updates)

    async def create_report(
        self,
        current_user: User,
        listing: Listing,
        report_data: CreateListingReportRequest,
    ) -> CreatedListingReportResponse:
        if listing.user_id == current_user.id:
            raise CannotReportOwnListingError()

        reason = await self.get_reason(report_data.reason_id)
        if not reason.is_active:
            raise ReportReasonInactiveError()

        if (
            reason.slug == OTHER_REPORT_REASON_SLUG
            and report_data.additional_info is None
        ):
            raise CustomReasonDetailsRequiredError()

        if await self.reports_repo.exists_pending_for_listing_and_reporter(
            listing_id=listing.id,
            reporter_id=current_user.id,
        ):
            raise DuplicatePendingListingReportError()

        try:
            async with self.uow:
                report = await self.reports_repo.create(
                    listing_id=listing.id,
                    reporter_id=current_user.id,
                    reason_id=reason.id,
                    additional_info=report_data.additional_info,
                    status=ReportStatus.PENDING,
                )
        except IntegrityError as exc:
            if await self.reports_repo.exists_pending_for_listing_and_reporter(
                listing_id=listing.id,
                reporter_id=current_user.id,
            ):
                raise DuplicatePendingListingReportError() from exc
            raise

        return self._build_created_report_response(report)

    async def list_reports(
        self,
        *,
        limit: int,
        cursor: str | None = None,
        status: ReportStatus | None = None,
        seen: ReportSeenFilter = ReportSeenFilter.ALL,
    ) -> ListReportsResponse:
        cursor_created_at, cursor_id = self._decode_reports_cursor(cursor)
        reports = await self.reports_repo.list_reports(
            limit=limit,
            status=status,
            seen=self._resolve_seen_filter(seen),
            cursor_created_at=cursor_created_at,
            cursor_id=cursor_id,
        )
        stats = await self.reports_repo.get_dashboard_stats()
        next_cursor = (
            self._encode_reports_cursor(reports[-1].created_at, reports[-1].id)
            if len(reports) == limit
            else None
        )
        return ListReportsResponse(
            stats=ReportsDashboardStats(
                new_today=stats.new_today,
                no_action=stats.no_action,
                unseen=stats.unseen,
            ),
            reports=[self._build_report_list_item(report) for report in reports],
            next_cursor=next_cursor,
        )

    async def get_report_detail(
        self,
        report: ListingReport,
        moderator: User,
    ) -> ReportDetailResponse:
        if report.seen_at is None:
            async with self.uow:
                await self.reports_repo.mark_seen(
                    report_id=report.id,
                    moderator_id=moderator.id,
                    seen_at=self._utc_now(),
                )
            report = await self.get_report(report.id)

        return self._build_report_detail_response(report)

    async def moderate_report(
        self,
        report: ListingReport,
        moderator: User,
        moderation_data: ModerateReportRequest,
    ) -> ReportDetailResponse:
        moderated_at = self._utc_now()
        resolved_status = self._resolve_moderation_status(moderation_data.action)

        async with self.uow:
            resolved = await self.reports_repo.resolve_pending_by_id(
                report_id=report.id,
                status=resolved_status,
                moderator_id=moderator.id,
                moderated_at=moderated_at,
                moderator_comment=moderation_data.comment,
            )
            if not resolved:
                raise ListingReportAlreadyResolvedError()

            if moderation_data.action == ReportDecisionAction.REMOVE_LISTING:
                await self.repos.listings.soft_delete_by_id(report.listing_id)
                await self.reports_repo.resolve_pending_for_listing(
                    listing_id=report.listing_id,
                    status=ReportStatus.LISTING_REMOVED,
                    moderator_id=moderator.id,
                    moderated_at=moderated_at,
                    moderator_comment=moderation_data.comment,
                    exclude_report_id=report.id,
                )
            elif moderation_data.action == ReportDecisionAction.BAN_USER:
                await self.repos.users.soft_delete_by_id(report.listing.user_id)
                await self.repos.listings.soft_delete_by_user_id(report.listing.user_id)
                await self.reports_repo.resolve_pending_for_user_listings(
                    user_id=report.listing.user_id,
                    status=ReportStatus.USER_BANNED,
                    moderator_id=moderator.id,
                    moderated_at=moderated_at,
                    moderator_comment=moderation_data.comment,
                    exclude_report_id=report.id,
                )

        return self._build_report_detail_response(await self.get_report(report.id))

    def _build_reason_summary(self, reason: ReportReason) -> ReportReasonSummary:
        return ReportReasonSummary(
            id=reason.id,
            slug=reason.slug,
            title=reason.title,
            description=reason.description,
        )

    def _build_seller_summary(self, listing: Listing) -> ReportSellerSummary:
        return ReportSellerSummary(
            id=listing.user.id,
            username=listing.user.username,
            display_name=listing.user.display_name,
        )

    def _build_listing_summary(self, listing: Listing) -> ReportListingSummary:
        return ReportListingSummary(
            id=listing.id,
            title=listing.title,
            price=listing.price,
            currency=listing.currency,
            status=listing.status,
            primary_image_url=self._build_primary_image_url(listing),
        )

    def _build_listing_detail(self, listing: Listing) -> ReportListingDetail:
        return ReportListingDetail(
            id=listing.id,
            title=listing.title,
            description=listing.description,
            price=listing.price,
            currency=listing.currency,
            status=listing.status,
            primary_image_url=self._build_primary_image_url(listing),
        )

    def _build_created_report_response(
        self,
        report: ListingReport,
    ) -> CreatedListingReportResponse:
        return CreatedListingReportResponse(
            id=report.id,
            listing_id=report.listing_id,
            reason=self._build_reason_summary(report.reason),
            additional_info=report.additional_info,
            status=report.status,
            created_at=report.created_at,
            updated_at=report.updated_at,
        )

    def _build_report_list_item(self, report: ListingReport) -> ReportListItem:
        return ReportListItem(
            id=report.id,
            status=report.status,
            created_at=report.created_at,
            seen=report.seen_at is not None,
            reason=self._build_reason_summary(report.reason),
            additional_info_preview=self._build_additional_info_preview(
                report.additional_info
            ),
            listing=self._build_listing_summary(report.listing),
            seller=self._build_seller_summary(report.listing),
        )

    def _build_report_detail_response(
        self,
        report: ListingReport,
    ) -> ReportDetailResponse:
        return ReportDetailResponse(
            id=report.id,
            status=report.status,
            created_at=report.created_at,
            updated_at=report.updated_at,
            additional_info=report.additional_info,
            reason=self._build_reason_summary(report.reason),
            listing=self._build_listing_detail(report.listing),
            seller=self._build_seller_summary(report.listing),
            seen_at=report.seen_at,
            seen_by_moderator_id=report.seen_by_moderator_id,
            moderated_at=report.moderated_at,
            moderator_id=report.moderator_id,
            moderator_comment=report.moderator_comment,
        )

    def _build_additional_info_preview(self, value: str | None) -> str | None:
        if value is None or len(value) <= ADDITIONAL_INFO_PREVIEW_LENGTH:
            return value

        return value[:ADDITIONAL_INFO_PREVIEW_LENGTH].rstrip() + "..."

    def _build_primary_image_url(self, listing: Listing) -> str | None:
        for listing_image in listing.images:
            if (
                isinstance(listing_image, ListingImage)
                and listing_image.image is not None
            ):
                return listing_image.image.url
        return None

    def _resolve_seen_filter(self, seen: ReportSeenFilter) -> bool | None:
        if seen == ReportSeenFilter.SEEN:
            return True
        if seen == ReportSeenFilter.UNSEEN:
            return False
        return None

    def _decode_reports_cursor(
        self,
        cursor: str | None,
    ) -> tuple[datetime.datetime | None, int | None]:
        if cursor is None:
            return None, None

        try:
            data = json.loads(base64.urlsafe_b64decode(cursor))
        except ValueError:
            return None, None

        if "created_at" not in data or "id" not in data:
            return None, None

        try:
            created_at = datetime.datetime.fromisoformat(data["created_at"])
        except TypeError, ValueError:
            return None, None
        if created_at.tzinfo is not None:
            created_at = created_at.astimezone(datetime.UTC).replace(tzinfo=None)

        return created_at, int(data["id"])

    def _encode_reports_cursor(
        self,
        created_at: datetime.datetime,
        report_id: int,
    ) -> str:
        data = {"created_at": created_at.isoformat(), "id": report_id}
        return base64.urlsafe_b64encode(json.dumps(data).encode()).decode()

    def _utc_now(self) -> datetime.datetime:
        return datetime.datetime.now(datetime.UTC).replace(tzinfo=None)

    def _resolve_moderation_status(
        self,
        action: ReportDecisionAction,
    ) -> ReportStatus:
        if action == ReportDecisionAction.DECLINE:
            return ReportStatus.DECLINED
        if action == ReportDecisionAction.REMOVE_LISTING:
            return ReportStatus.LISTING_REMOVED
        return ReportStatus.USER_BANNED
