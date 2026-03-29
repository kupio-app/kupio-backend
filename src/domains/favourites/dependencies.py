from fastapi import Depends

from src.core.database.uow import UoW
from src.core.dependencies import RepositoriesDeps, get_uow

from .service import FavouritesService


def get_favourites_service(
    repos: RepositoriesDeps,
    uow: UoW = Depends(get_uow),
) -> FavouritesService:
    return FavouritesService(repos=repos, uow=uow)
