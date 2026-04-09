from fastapi import APIRouter, Depends

from src.core.dependencies import get_current_user
from src.core.utils.pagination import LimitOffsetPaginationParams
from src.domains.users.models import User

from .dependencies import get_payments_service
from .schemas import BalanceTransactionResponse
from .service import PaymentsService

router = APIRouter()


@router.get("/transactions", response_model=list[BalanceTransactionResponse])
async def list_transactions(
    pagination: LimitOffsetPaginationParams = Depends(),
    current_user: User = Depends(get_current_user),
    service: PaymentsService = Depends(get_payments_service),
):
    return await service.list_transactions(
        current_user,
        limit=pagination.limit,
        offset=pagination.offset,
    )
