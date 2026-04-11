import uuid

from src.core.database.base_model import UUID
from src.domains.images.consts import CONTENT_TYPE_TO_EXTENSION


def build_listing_image_key(listing_id: UUID, content_type: str) -> str:
    ext = CONTENT_TYPE_TO_EXTENSION[content_type]
    return f"listings/{listing_id}/{uuid.uuid4()}.{ext}"


def build_avatar_key(user_id: UUID, content_type: str) -> str:
    ext = CONTENT_TYPE_TO_EXTENSION[content_type]
    return f"users/{user_id}/avatar/{uuid.uuid4()}.{ext}"
