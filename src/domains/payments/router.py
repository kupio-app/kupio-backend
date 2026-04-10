from fastapi import APIRouter, Depends, Request, status, Header

from src.core.dependencies import get_current_user
from src.core.utils.pagination import LimitOffsetPaginationParams
from src.domains.users.models import User

from .dependencies import get_payments_service
from .schemas import BalanceTransactionResponse, CheckoutRequest, CheckoutResponse
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


@router.post(
    "/checkout", response_model=CheckoutResponse, status_code=status.HTTP_201_CREATED
)
async def create_checkout(
    body: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    service: PaymentsService = Depends(get_payments_service),
):
    return await service.create_checkout_session(current_user, body)


@router.post("/webhooks/stripe", include_in_schema=False)
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(),
    service: PaymentsService = Depends(get_payments_service),
):
    payload = await request.body()
    await service.handle_webhook(payload, stripe_signature)
    return {"status": "ok"}
