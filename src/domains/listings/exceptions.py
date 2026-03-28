from src.core.exceptions import ForbiddenError, NotFoundError


class ListingNotFoundError(NotFoundError):
    detail = "Listing not found"


class ListingOwnershipError(ForbiddenError):
    detail = "You do not have permission to manage this listing"
