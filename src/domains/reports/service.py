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

