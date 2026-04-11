from fastapi import Depends

from src.core.database.uow import UoW
from src.core.dependencies import RepositoriesDeps, get_uow, get_s3_storage_service
from src.core.storage.s3 import S3StorageService
from src.domains.images.service import ImageService


def get_images_service(
    repos: RepositoriesDeps,
    uow: UoW = Depends(get_uow),
    storage: S3StorageService = Depends(get_s3_storage_service),
):
    return ImageService(repos=repos, uow=uow, storage=storage)
