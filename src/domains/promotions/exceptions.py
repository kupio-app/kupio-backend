from src.core.exceptions import BadRequestError, ConflictError, NotFoundError


class PromotionPacketNotFoundError(NotFoundError):
    detail = "Promotion packet not found"


class PromotionPacketInactiveError(BadRequestError):
    detail = "Promotion packet is not available"


class ListingNotPromotableError(BadRequestError):
    detail = "Only active listings can be promoted"


class DuplicateActivePromotionError(ConflictError):
    detail = "An active promotion of this type already exists for this listing"


class ListingPromotionNotFoundError(NotFoundError):
    detail = "Listing promotion not found"
