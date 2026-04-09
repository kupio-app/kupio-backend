from fastapi import Depends

from src.core.database.uow import UoW
from src.core.dependencies import RepositoriesDeps, get_uow

from .service import PaymentsService


def get_payments_service(
    repos: RepositoriesDeps,
    uow: UoW = Depends(get_uow),
) -> PaymentsService:
    return PaymentsService(repos=repos, uow=uow)
