from pydantic import BaseModel

from src.core.database.base_model import UUID


class ListingImageResponse(BaseModel):
    id: UUID
    url: str
    sort_order: int


class UpdateListingImagesOrderRequest(BaseModel):
    image_ids: list[UUID]
