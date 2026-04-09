import datetime

from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

from .enums import PromotionStatus, PromotionType


class PromotionPacketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    type: PromotionType
    duration_days: int
    price: int
    is_active: bool


class PromotionPacketCreateRequest(BaseModel):
    name: str = Field(min_length=3, max_length=100)
    description: str | None = Field(None, max_length=255)
    type: PromotionType
    duration_days: int = Field(gt=0)
    price: int = Field(gt=0)


class PromotionPacketUpdateRequest(BaseModel):
    name: str = Field(None, min_length=3, max_length=100)
    description: str | None = Field(None, max_length=255)
    price: int = Field(None, gt=0)
    is_active: bool = None


class ListingPromotionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    listing_id: UUID
    packet: PromotionPacketResponse
    transaction_id: UUID
    starts_at: datetime.datetime
    expires_at: datetime.datetime
    status: PromotionStatus
    created_at: datetime.datetime


class PurchasePromotionRequest(BaseModel):
    packet_id: int


class ListPromotionsResponse(BaseModel):
    promotions: list[ListingPromotionResponse]
    next_cursor: str | None
