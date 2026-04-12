from uuid import UUID

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from src.core.database.uow import UoW
from src.core.dependencies import RepositoriesDeps, get_current_user, get_uow
from src.domains.auth.exceptions import InvalidTokenError, InvalidTokenPayloadError
from src.domains.categories.dependencies import get_categories_service
from src.domains.categories.service import CategoriesService
from src.domains.filter_definitions.dependencies import get_filter_def_service
from src.domains.filter_definitions.service import FilterDefinitionsService
from src.domains.users.models import User

from .exceptions import ListingOwnershipError
from .models import Listing
from .service import ListingsService


optional_oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login", auto_error=False
)


def get_listings_service(
    repos: RepositoriesDeps,
    uow: UoW = Depends(get_uow),
    categories_service: CategoriesService = Depends(get_categories_service),
    filter_definitions_service: FilterDefinitionsService = Depends(
        get_filter_def_service
    ),
) -> ListingsService:
    return ListingsService(
        repos=repos,
        uow=uow,
        categories_service=categories_service,
        filter_definitions_service=filter_definitions_service,
    )


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


async def get_optional_listing_viewer(
    repos: RepositoriesDeps,
    token: str | None = Depends(optional_oauth2_scheme),
) -> User | None:
    if token is None:
        return None

    try:
        return await get_current_user(repos=repos, token=token)
    except InvalidTokenError, InvalidTokenPayloadError:
        return None
