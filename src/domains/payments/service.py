import uuid

from stripe import StripeClient, Webhook as StripeWebhook, error as stripe_error
from stripe.params.checkout import SessionCreateParams, SessionCreateParamsLineItem

from src.core.config import StripeConfig
from src.core.database.repositories import Repositories
from src.core.database.uow import UoW
from src.domains.payments.schemas import CheckoutRequest, CheckoutResponse
from src.domains.payments.enums import PaymentSessionStatus, TransactionType
from src.domains.payments.exceptions import WebhookSignatureError
from src.domains.users.models import User
from .consts import PAYMENT_CURRENCY, STRIPE_TOPUP_PRODUCT_NAME
from .models import BalanceTransaction


class PaymentsService:
    def __init__(
        self,
        repos: Repositories,
        uow: UoW,
        *,
        stripe_client: StripeClient,
        stripe_config: StripeConfig,
    ) -> None:
        self.repos = repos
        self.uow = uow
        self.stripe_client = stripe_client
        self.stripe_config = stripe_config

    async def list_transactions(
        self,
        current_user: User,
        *,
        limit: int,
        offset: int = 0,
    ) -> list[BalanceTransaction]:
        return await self.repos.balance_transactions.get_by_user(
            current_user.id,
            limit=limit,
            offset=offset,
        )

    async def create_checkout_session(
        self, current_user: User, checkout_req: CheckoutRequest
    ) -> CheckoutResponse:
        payment_session_id = uuid.uuid4()
        session = await self.stripe_client.v1.checkout.sessions.create_async(
            SessionCreateParams(
                mode="payment",
                line_items=[
                    SessionCreateParamsLineItem(
                        price_data={
                            "currency": PAYMENT_CURRENCY,
                            "unit_amount": checkout_req.amount,
                            "product_data": {"name": STRIPE_TOPUP_PRODUCT_NAME},
                        },
                        quantity=1,
                    )
                ],
                success_url=self.stripe_config.success_url,
                cancel_url=self.stripe_config.cancel_url,
                metadata={"internal_session_id": str(payment_session_id)},
            )
        )

        async with self.uow:
            await self.repos.payments_sessions.create(
                session_id=payment_session_id,
                user_id=current_user.id,
                amount=checkout_req.amount,
                stripe_session_id=session.id,
            )

        return CheckoutResponse(checkout_url=session.url, session_id=payment_session_id)

    async def handle_webhook(self, payload: bytes, sig_header: str | None) -> None:
        if sig_header is None:
            raise WebhookSignatureError()

        try:
            event = StripeWebhook.construct_event(
                payload,
                sig_header,
                self.stripe_config.webhook_secret.get_secret_value(),
            )
        except stripe_error.SignatureVerificationError as exc:
            raise WebhookSignatureError() from exc

        event_type = event["type"]
        session_object = event["data"]["object"]

        if event_type == "checkout.session.completed":
            checkout = await self.repos.payments_sessions.get_by_stripe_id(
                session_object["id"]
            )
            if checkout is None or checkout.status != PaymentSessionStatus.PENDING:
                return

            payment_intent: str | None = None
            try:
                payment_intent = session_object.get("payment_intent")
            except AttributeError:
                pass  # Idk why, but developers of StripeObject class decided to remove ability of save getter

            async with self.uow:
                await self.repos.payments_sessions.update_status(
                    checkout.id,
                    status=PaymentSessionStatus.COMPLETED,
                    payment_intent_id=payment_intent,
                )

                await self.repos.users.add_balance(checkout.user_id, checkout.amount)
                await self.repos.balance_transactions.create(
                    user_id=checkout.user_id,
                    amount=checkout.amount,
                    _type=TransactionType.TOP_UP,
                )

        elif event_type == "checkout.session.expired":
            checkout = await self.repos.payments_sessions.get_by_stripe_id(
                session_object["id"]
            )
            if checkout is None or checkout.status != PaymentSessionStatus.PENDING:
                return

            async with self.uow:
                await self.repos.payments_sessions.update_status(
                    checkout.id,
                    status=PaymentSessionStatus.EXPIRED,
                )
