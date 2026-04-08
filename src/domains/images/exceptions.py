from src.core.exceptions import UnprocessableEntityError, NotFoundError
from .consts import MAX_IMAGE_SIZE_BYTES, ALLOWED_CONTENT_TYPES


class ImageMaxSizeError(UnprocessableEntityError):
    detail = f"Maximum allowed size for image is {MAX_IMAGE_SIZE_BYTES}"


class ImageContentTypeError(UnprocessableEntityError):
    detail = f"Allowed content types are {ALLOWED_CONTENT_TYPES}"


class ListingImageNotFoundError(NotFoundError):
    detail = "Listing image not found"
