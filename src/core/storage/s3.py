from typing import BinaryIO

import boto3
from fastapi import FastAPI
from starlette.concurrency import run_in_threadpool

from src.core.config import S3Config, AppConfig


class S3StorageService:
    def __init__(self, config: S3Config):
        self._bucket = config.bucket
        self._region = config.region
        self._client = boto3.client(
            "s3",
            region_name=self._region,
            aws_access_key_id=config.access_key_id,
            aws_secret_access_key=config.secret_access_key.get_secret_value(),
        )

    def upload_file(self, fileobj: BinaryIO, key: str, content_type: str):
        self._client.upload_fileobj(
            fileobj,
            self._bucket,
            key,
            ExtraArgs={"ContentType": content_type},
        )

    def delete_object(self, key: str):
        self._client.delete_object(
            Bucket=self._bucket,
            Key=key,
        )

    def close(self):
        self._client.close()


def init_s3(app: FastAPI, config: AppConfig) -> S3StorageService:
    service = S3StorageService(config.s3)
    app.state.s3_storage = service
    return service


async def shutdown_s3(app: FastAPI):
    service = getattr(app.state, "s3_storage", None)
    if service is not None:
        await run_in_threadpool(service.close)
