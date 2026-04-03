import datetime
from uuid import UUID

from sqlalchemy import and_, or_

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
        cursor_created_at: datetime.datetime | None = None,
        cursor_id: UUID | None = None,
    ) -> list[BalanceTransaction]:
        conditions = [BalanceTransaction.user_id == user_id]

        if cursor_created_at is not None and cursor_id is not None:
            conditions.append(
                or_(
                    BalanceTransaction.created_at < cursor_created_at,
                    and_(
                        BalanceTransaction.created_at == cursor_created_at,
                        BalanceTransaction.id < cursor_id,
                    ),
                )
            )

        return await self._get_many(
            BalanceTransaction,
            *conditions,
            limit=limit,
            order_by=[
                BalanceTransaction.created_at.desc(),
                BalanceTransaction.id.desc(),
            ],
        )
