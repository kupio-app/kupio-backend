import stripe

from fastapi import Depends, Request

from src.core.config import StripeConfig, get_config
from src.core.database.uow import UoW
from src.core.dependencies import RepositoriesDeps, get_uow

from .service import PaymentsService


def get_stripe_config() -> StripeConfig:
    return get_config().stripe


def get_stripe_client(request: Request) -> stripe.StripeClient:
    return request.app.state.stripe_client


def get_payments_service(
    repos: RepositoriesDeps,
    uow: UoW = Depends(get_uow),
    stripe_client: stripe.StripeClient = Depends(get_stripe_client),
    stripe_config: StripeConfig = Depends(get_stripe_config),
) -> PaymentsService:
    return PaymentsService(
        repos=repos,
        uow=uow,
        stripe_client=stripe_client,
        stripe_config=stripe_config,
    )
