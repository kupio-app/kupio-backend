from fastapi import APIRouter

from .auth.router import router as auth_router
from .categories.router import router as categories_router
from .filter_definitions.router import router as filter_definitions_router
from .favourites.router import router as favourites_router
from .listings.router import router as listings_router
from .users.router import router as users_router
from .images.router import router as image_router

api_router = APIRouter()
api_router.include_router(users_router, tags=["Users"], prefix="/users")
api_router.include_router(auth_router, tags=["Auth"], prefix="/auth")
api_router.include_router(categories_router, tags=["Categories"], prefix="/categories")
api_router.include_router(
    filter_definitions_router,
    tags=["Filter Definitions"],
    prefix="/categories/{category_id}/filters",
)
api_router.include_router(
    favourites_router,
    tags=["Favourites"],
    prefix="/listings/favourites",
)
api_router.include_router(listings_router, tags=["Listings"], prefix="/listings")
api_router.include_router(image_router, tags=["Images"])
