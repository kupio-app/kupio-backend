from pydantic import BaseModel

from src.core.database.base_model import UUID


class ImageResponse(BaseModel):
    id: UUID
    url: str
    sort_order: int
