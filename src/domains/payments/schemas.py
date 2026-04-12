import datetime

from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

from .enums import TransactionType


class BalanceTransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    amount: int
    type: TransactionType
    created_at: datetime.datetime


class CheckoutRequest(BaseModel):
    amount: int = Field(gt=0, description="Amount in cents to top up the balance")


class CheckoutResponse(BaseModel):
    checkout_url: str
    session_id: UUID
