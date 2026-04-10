from src.domains.reports.exceptions import (
    DuplicateReportReasonSlugError,
    ListingReportNotFoundError,
    OtherReasonCannotBeDeactivatedError,
    ReportReasonNotFoundError,
    ReservedOtherReasonSlugError,
)
from src.domains.reports.models import ListingReport, ReportReason
from src.domains.reports.schemas import (
    ReportReasonCreateRequest,
    ReportReasonUpdateRequest,
)
from src.core.database.repositories import Repositories
from src.core.database.uow import UoW
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

        async with self.uow:
            return await self.report_reasons_repo.create(**reason_data.model_dump())

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
