from sqlalchemy import select

from src.domains.payments.enums import PaymentSessionStatus, TransactionType
from src.domains.payments.models import BalanceTransaction, PaymentSession
from src.domains.users.models import User
from tests.helpers.auth import auth_header, register_user


def _auth_header(token: str) -> dict:
    return auth_header(token)


async def _register(client, *, email: str, username: str) -> str:
    data = await register_user(client, email=email, username=username)
    return data["access_token"]


async def test_create_checkout_session_returns_checkout_url(client, session_factory):
    token = await _register(client, email="buyer@example.com", username="buyer")

    resp = await client.post(
        "/api/payments/checkout",
        headers=_auth_header(token),
        json={"amount": 1500},
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["session_id"]
    assert body["checkout_url"] == "https://checkout.example/session"

    async with session_factory() as session:
        row = await session.scalar(select(PaymentSession))
        assert row is not None
        assert row.amount == 1500
        assert row.status == PaymentSessionStatus.PENDING
        assert row.stripe_session_id == "cs_test_123"


async def test_checkout_webhook_completed_credits_balance(
    monkeypatch, client, session_factory
):
    token = await _register(client, email="buyer2@example.com", username="buyer2")

    await client.post(
        "/api/payments/checkout",
        headers=_auth_header(token),
        json={"amount": 2000},
    )

    def _construct_event(payload, sig_header, secret):
        return {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_123",
                    "payment_intent": "pi_test_123",
                }
            },
        }

    monkeypatch.setattr(
        "src.domains.payments.service.StripeWebhook.construct_event",
        _construct_event,
    )

    resp = await client.post(
        "/api/payments/webhooks/stripe",
        headers={"stripe-signature": "sig-test"},
        content=b"{}",
    )

    assert resp.status_code == 200

    async with session_factory() as session:
        checkout = await session.scalar(select(PaymentSession))
        assert checkout is not None
        assert checkout.status == PaymentSessionStatus.COMPLETED
        assert checkout.stripe_payment_intent_id == "pi_test_123"

        transactions = (await session.scalars(select(BalanceTransaction))).all()
        assert len(transactions) == 1
        assert transactions[0].type == TransactionType.TOP_UP
        assert transactions[0].amount == 2000

        user = await session.scalar(select(User).where(User.username == "buyer2"))
        assert user is not None
        assert user.balance == 2000


async def test_checkout_webhook_expired_updates_status(
    monkeypatch, client, session_factory
):
    token = await _register(client, email="buyer3@example.com", username="buyer3")

    await client.post(
        "/api/payments/checkout",
        headers=_auth_header(token),
        json={"amount": 2500},
    )

    monkeypatch.setattr(
        "src.domains.payments.service.StripeWebhook.construct_event",
        lambda payload, sig_header, secret: {
            "type": "checkout.session.expired",
            "data": {"object": {"id": "cs_test_123"}},
        },
    )

    resp = await client.post(
        "/api/payments/webhooks/stripe",
        headers={"stripe-signature": "sig-test"},
        content=b"{}",
    )

    assert resp.status_code == 200

    async with session_factory() as session:
        checkout = await session.scalar(select(PaymentSession))
        assert checkout is not None
        assert checkout.status == PaymentSessionStatus.EXPIRED
        assert await session.scalar(select(BalanceTransaction)) is None
