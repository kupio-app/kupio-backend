import datetime

from uuid import UUID
from pydantic import BaseModel, ConfigDict

from .enums import TransactionType


class BalanceTransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    amount: int
    type: TransactionType
    created_at: datetime.datetime
