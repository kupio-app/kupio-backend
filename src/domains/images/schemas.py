from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from src.core.database.base_model import UUID


class ListingImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    # Public API exposes the Image id, not the listing_images join-row id.
    id: UUID = Field(validation_alias=AliasChoices("image_id", "id"))
    url: str
    sort_order: int


class UpdateListingImagesOrderRequest(BaseModel):
    image_ids: list[UUID]
