from src.core.exceptions import (
    ForbiddenError,
    NotFoundError,
    UnprocessableEntityError,
)


class ListingNotFoundError(NotFoundError):
    detail = "Listing not found"


class ListingOwnershipError(ForbiddenError):
    detail = "You do not have permission to manage this listing"


class InvalidListingPriceRangeError(UnprocessableEntityError):
    detail = "min_price must be less than or equal to max_price"
