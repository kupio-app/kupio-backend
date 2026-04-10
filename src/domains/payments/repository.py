from uuid import UUID

from src.core.database.base_repository import BaseRepository
from .enums import PaymentSessionStatus, TransactionType
from .models import BalanceTransaction, PaymentSession


class BalanceTransactionRepository(BaseRepository):
    async def create(
        self,
        *,
        user_id: UUID,
        amount: int,
        _type: TransactionType,
    ) -> BalanceTransaction:
        return await self._add(
            BalanceTransaction,
            user_id=user_id,
            amount=amount,
            type=_type,
        )

    async def get_by_user(
        self,
        user_id: UUID,
        *,
        limit: int,
        offset: int = 0,
    ) -> list[BalanceTransaction]:
        return await self._get_many(
            BalanceTransaction,
            BalanceTransaction.user_id == user_id,
            limit=limit,
            offset=offset,
            order_by=[
                BalanceTransaction.created_at.desc(),
                BalanceTransaction.id.desc(),
            ],
        )


class PaymentSessionRepository(BaseRepository):
    async def create(
        self, *, session_id: UUID, user_id: UUID, amount: int, stripe_session_id: str
    ) -> PaymentSession:
        return await self._add(
            PaymentSession,
            id=session_id,
            user_id=user_id,
            amount=amount,
            stripe_session_id=stripe_session_id,
        )

    async def get_by_stripe_id(self, stripe_session_id: str) -> PaymentSession | None:
        return await self._get(
            PaymentSession,
            PaymentSession.stripe_session_id == stripe_session_id,
        )

    async def update_status(
        self,
        session_id: UUID,
        *,
        status: PaymentSessionStatus,
        stripe_session_id: str | None = None,
        payment_intent_id: str | None = None,
    ) -> None:
        kwargs: dict[str, object] = {"status": status}
        if stripe_session_id is not None:
            kwargs["stripe_session_id"] = stripe_session_id
        if payment_intent_id is not None:
            kwargs["stripe_payment_intent_id"] = payment_intent_id

        await self._update(
            PaymentSession,
            [PaymentSession.id == session_id],
            load_result=False,
            **kwargs,
        )
