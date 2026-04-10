from fastapi import Depends

from src.core.database.uow import UoW
from src.core.dependencies import RepositoriesDeps, get_uow

from .service import ReportsService


def get_reports_service(
    repos: RepositoriesDeps,
    uow: UoW = Depends(get_uow),
) -> ReportsService:
    return ReportsService(repos=repos, uow=uow)

