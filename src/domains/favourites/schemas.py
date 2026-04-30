from uuid import UUID

from pydantic import BaseModel


class FavouritedListingsIds(BaseModel):
    listings_ids: list[UUID]
