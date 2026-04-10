from fastapi import APIRouter, Depends, Query, status

from src.core.dependencies import get_current_user, require_roles
from src.core.utils.pagination import PaginationParams
from src.domains.listings.dependencies import get_listing_by_id
from src.domains.listings.models import Listing
from src.domains.users.enums import UserRole
from src.domains.users.models import User

from .dependencies import get_report_by_id, get_report_reason_by_id, get_reports_service
from .enums import ReportSeenFilter, ReportStatus
from .models import ListingReport, ReportReason
from .schemas import (
    CreateListingReportRequest,
    CreatedListingReportResponse,
    ListReportsResponse,
    ReportDetailResponse,
    ReportReasonCreateRequest,
    ReportReasonResponse,
    ReportReasonUpdateRequest,
)
from .service import ReportsService

router = APIRouter()


@router.get("/reports/reasons", response_model=list[ReportReasonResponse])
async def get_report_reasons(
    service: ReportsService = Depends(get_reports_service),
):
    return await service.list_active_reasons()


@router.get("/reports/reasons/all", response_model=list[ReportReasonResponse])
async def get_all_report_reasons(
    service: ReportsService = Depends(get_reports_service),
    _=Depends(require_roles(UserRole.MODERATOR)),
):
    return await service.list_all_reasons()


@router.post(
    "/reports/reasons",
    response_model=ReportReasonResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_report_reason(
    reason_data: ReportReasonCreateRequest,
    service: ReportsService = Depends(get_reports_service),
    _=Depends(require_roles(UserRole.MODERATOR)),
):
    return await service.create_reason(reason_data)


@router.put("/reports/reasons/{reason_id}", response_model=ReportReasonResponse)
async def update_report_reason(
    reason_data: ReportReasonUpdateRequest,
    reason: ReportReason = Depends(get_report_reason_by_id),
    service: ReportsService = Depends(get_reports_service),
    _=Depends(require_roles(UserRole.MODERATOR)),
):
    return await service.update_reason(reason, reason_data)


@router.post(
    "/listings/{listing_id}/reports",
    response_model=CreatedListingReportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_listing_report(
    report_data: CreateListingReportRequest,
    listing: Listing = Depends(get_listing_by_id),
    current_user: User = Depends(get_current_user),
    service: ReportsService = Depends(get_reports_service),
):
    return await service.create_report(current_user, listing, report_data)


@router.get("/reports", response_model=ListReportsResponse)
async def get_reports(
    pagination: PaginationParams = Depends(),
    status: ReportStatus | None = Query(default=None),
    seen: ReportSeenFilter = Query(default=ReportSeenFilter.ALL),
    current_user: User = Depends(require_roles(UserRole.MODERATOR)),
    service: ReportsService = Depends(get_reports_service),
):
    return await service.list_reports(
        limit=pagination.limit,
        cursor=pagination.cursor,
        status=status,
        seen=seen,
    )


@router.get("/reports/{report_id}", response_model=ReportDetailResponse)
async def get_report_detail(
    report: ListingReport = Depends(get_report_by_id),
    current_user: User = Depends(require_roles(UserRole.MODERATOR)),
    service: ReportsService = Depends(get_reports_service),
):
    return await service.get_report_detail(report, current_user)
