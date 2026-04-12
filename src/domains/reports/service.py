import datetime

from sqlalchemy.exc import IntegrityError

from src.core.utils.pagination import decode_int_cursor, encode_int_cursor
from src.domains.listings.models import Listing
from src.domains.users.models import Moderator, User
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
    ReportListItem,
    ReportReasonCreateRequest,
    ReportReasonUpdateRequest,
    ReportsDashboardStats,
    CreateListingReportRequest,
)
from src.core.database.repositories import Repositories
from src.core.database.uow import UoW
from .consts import OTHER_REPORT_REASON_SLUG, ADDITIONAL_INFO_PREVIEW_LENGTH
from .enums import ReportDecisionAction, ReportSeenFilter, ReportStatus
from .repository import ReportReasonsRepository, ReportsRepository


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
        updates = reason_data.model_dump(exclude_unset=True)
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

        return CreatedListingReportResponse.build_from(report)

    async def list_reports(
        self,
        *,
        limit: int,
        cursor: str | None = None,
        status: ReportStatus | None = None,
        seen: ReportSeenFilter = ReportSeenFilter.ALL,
    ) -> ListReportsResponse:
        cursor_created_at, cursor_id = (
            decode_int_cursor(cursor) if cursor else (None, None)
        )
        reports = await self.reports_repo.list_reports(
            limit=limit,
            status=status,
            seen=self._resolve_seen_filter(seen),
            cursor_created_at=cursor_created_at,
            cursor_id=cursor_id,
        )
        stats = await self.reports_repo.get_dashboard_stats()
        next_cursor = (
            encode_int_cursor(reports[-1].created_at, reports[-1].id)
            if len(reports) == limit
            else None
        )
        return ListReportsResponse(
            stats=ReportsDashboardStats(
                new_today=stats.new_today,
                no_action=stats.no_action,
                unseen=stats.unseen,
            ),
            reports=[
                ReportListItem.build_from(
                    report,
                    additional_info_preview_length=ADDITIONAL_INFO_PREVIEW_LENGTH,
                )
                for report in reports
            ],
            next_cursor=next_cursor,
        )

    async def get_report_detail(
        self,
        report: ListingReport,
        moderator: Moderator,
    ) -> ReportDetailResponse:
        now = self._utc_now()
        if report.seen_at is None:
            async with self.uow:
                await self.reports_repo.mark_seen(
                    report_id=report.id,
                    moderator_id=moderator.id,
                    seen_at=now,
                )
                await self.repos.moderators.touch_last_action(moderator.id, at=now)
            report = await self.get_report(report.id)
        else:
            async with self.uow:
                await self.repos.moderators.touch_last_action(moderator.id, at=now)
            report = await self.get_report(report.id)

        return ReportDetailResponse.build_from(report)

    async def moderate_report(
        self,
        report: ListingReport,
        moderator: Moderator,
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
            await self.repos.moderators.touch_last_action(moderator.id, at=moderated_at)

        return ReportDetailResponse.build_from(await self.get_report(report.id))

    def _resolve_seen_filter(self, seen: ReportSeenFilter) -> bool | None:
        if seen == ReportSeenFilter.SEEN:
            return True
        if seen == ReportSeenFilter.UNSEEN:
            return False
        return None

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
