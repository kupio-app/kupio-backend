from typing import BinaryIO
from urllib.parse import quote

import boto3

from src.core.config import S3Config


class S3StorageService:
    def __init__(self, config: S3Config):
        self.bucket = config.bucket
        self.region = config.region
        self.client = boto3.client(
            "s3",
            region_name=self.region,
            aws_access_key_id=config.access_key_id,
            aws_secret_access_key=config.secret_access_key.get_secret_value(),
        )

    def upload_file(self, fileobj: BinaryIO, key: str, content_type: str):
        self.client.upload_fileobj(
            fileobj,
            self.bucket,
            key,
            ExtraArgs={"ContentType": content_type},
        )

    def delete_object(self, key: str):
        self.client.delete_object(
            Bucket=self.bucket,
            Key=key,
        )

    def build_public_url(self, key: str) -> str:
        return f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{quote(key, safe='/')}"
