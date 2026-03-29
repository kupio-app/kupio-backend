from src.core.exceptions import ConflictError, ForbiddenError, NotFoundError


class ListingAlreadyFavouritedError(ConflictError):
    detail = "Listing is already in favourites"


class ListingNotInFavouritesError(NotFoundError):
    detail = "Listing is not in favourites"


class CannotFavouriteOwnListingError(ForbiddenError):
    detail = "You cannot favourite your own listing"
