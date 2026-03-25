import datetime

from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.domains.listings.enums import CurrencyEnum, ListingStatus


class ListingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str
    price: int
    currency: CurrencyEnum
    status: ListingStatus
    user_id: UUID
    category_id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime | None


class ListListingsResponse(BaseModel):
    listings: list[ListingResponse]
    next_cursor: str | None


class ListingRequest(BaseModel):
    title: str = Field(min_length=10, max_length=255)
    description: str = Field(min_length=50, max_length=5000)
    price: int = Field(ge=0, lt=10_000_000)
    is_free: bool = False
    is_tradable: bool = False
    currency: CurrencyEnum
    category_id: int

    @model_validator(mode="after")
    def check_price(self) -> "ListingRequest":
        if not self.is_free and not self.is_tradable and self.price == 0:
            raise ValueError(
                "Price must be greater than 0 for non-free and non-tradable listings"
            )

        return self


class ListingStatusUpdateRequest(BaseModel):
    status: ListingStatus
