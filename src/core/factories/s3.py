from fastapi import FastAPI
from starlette.concurrency import run_in_threadpool

from src.core.config import AppConfig
from src.core.storage.s3 import S3StorageService


def init_s3(app: FastAPI, config: AppConfig) -> S3StorageService:
    service = S3StorageService(config.s3)
    app.state.s3_storage = service
    return service


async def shutdown_s3(app: FastAPI) -> None:
    service = getattr(app.state, "s3_storage", None)
    if service is not None:
        await run_in_threadpool(service.close)
