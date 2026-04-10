from typing import Final


CONTENT_TYPE_TO_EXTENSION: Final[dict[str, str]] = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}

ALLOWED_CONTENT_TYPES: Final[tuple[str, ...]] = tuple(CONTENT_TYPE_TO_EXTENSION)

MAX_IMAGE_SIZE_BYTES: Final[int] = 10 * 1024 * 1024  # 10mb
