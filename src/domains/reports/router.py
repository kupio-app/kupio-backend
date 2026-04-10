from fastapi import APIRouter, Depends, status

from src.core.dependencies import require_roles
from src.domains.users.enums import UserRole

from .dependencies import get_report_reason_by_id, get_reports_service
from .models import ReportReason
from .schemas import (
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
