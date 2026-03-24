from uuid import UUID

from fastapi import Depends

from src.core.database.uow import UoW
from src.core.dependencies import RepositoriesDeps, get_current_user, get_uow
from src.domains.users.models import User

from .exceptions import ListingOwnershipError
from .models import Listing
from .service import ListingsService


def get_listings_service(
    repos: RepositoriesDeps,
    uow: UoW = Depends(get_uow),
) -> ListingsService:
    return ListingsService(repos=repos, uow=uow)


async def get_listing_by_id(
    listing_id: UUID,
    service: ListingsService = Depends(get_listings_service),
) -> Listing:
    return await service.get_listing(listing_id)


async def get_owned_listing_by_id(
    listing: Listing = Depends(get_listing_by_id),
    current_user: User = Depends(get_current_user),
) -> Listing:
    if listing.user_id != current_user.id:
        raise ListingOwnershipError()

    return listing
