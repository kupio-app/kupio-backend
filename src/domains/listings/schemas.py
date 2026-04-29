import datetime
from typing import TYPE_CHECKING, Any

from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.domains.categories.schemas import CategorySlim
from src.domains.images.schemas import ListingImageResponse
from src.domains.listings.enums import CurrencyEnum, ListingStatus

if TYPE_CHECKING:
    from .repository import OwnerListingStats


class ListingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str
    price: int
    currency: CurrencyEnum
    status: ListingStatus
    user_id: UUID
    category: CategorySlim
    custom_filters: dict[str, Any] | None
    images: list[ListingImageResponse] = Field(default_factory=list)
    created_at: datetime.datetime
    updated_at: datetime.datetime | None
    seen_count: int = 0


class ListListingsResponse(BaseModel):
    listings: list[ListingResponse]
    next_cursor: str | None


class OwnerListingResponse(ListingResponse):
    seen_count: int
    favourites_count: int
    chats_count: int
    is_promoted: bool
    promotion_expires_at: datetime.datetime | None

    @classmethod
    def build_from(cls, listing_stats: "OwnerListingStats") -> "OwnerListingResponse":
        listing_data = ListingResponse.model_validate(listing_stats.listing).model_dump(
            exclude={"seen_count"}
        )
        return cls(
            **listing_data,
            seen_count=listing_stats.seen_count,
            favourites_count=listing_stats.favourites_count,
            chats_count=listing_stats.chats_count,
            is_promoted=listing_stats.is_promoted,
            promotion_expires_at=listing_stats.promotion_expires_at,
        )


class ListOwnerListingsResponse(BaseModel):
    listings: list[OwnerListingResponse]
    next_cursor: str | None


class ListingRequest(BaseModel):
    title: str = Field(min_length=8, max_length=255)
    description: str = Field(min_length=50, max_length=5000)
    price: int = Field(ge=0, lt=10_000_000)
    is_free: bool = False
    is_tradable: bool = False
    currency: CurrencyEnum
    category_id: int
    custom_filters: dict[str, Any] | None = None

    @model_validator(mode="after")
    def check_price(self) -> "ListingRequest":
        if not self.is_free and not self.is_tradable and self.price == 0:
            raise ValueError(
                "Price must be greater than 0 for non-free and non-tradable listings"
            )

        return self


class ListingStatusUpdateRequest(BaseModel):
    status: ListingStatus
