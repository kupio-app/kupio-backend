from uuid import UUID

from src.core.database.base_repository import BaseRepository
from .enums import TransactionType
from .models import BalanceTransaction


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
