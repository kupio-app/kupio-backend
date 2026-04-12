from fastapi import Depends

from src.core.database.uow import UoW
from src.core.dependencies import RepositoriesDeps, get_uow
from .models import ListingReport, ReportReason

from .service import ReportsService


def get_reports_service(
    repos: RepositoriesDeps,
    uow: UoW = Depends(get_uow),
) -> ReportsService:
    return ReportsService(repos=repos, uow=uow)


async def get_report_reason_by_id(
    reason_id: int,
    service: ReportsService = Depends(get_reports_service),
) -> ReportReason:
    return await service.get_reason(reason_id)


async def get_report_by_id(
    report_id: int,
    service: ReportsService = Depends(get_reports_service),
) -> ListingReport:
    return await service.get_report(report_id)
