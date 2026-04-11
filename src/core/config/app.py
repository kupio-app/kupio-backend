from pydantic import BaseModel, Field

from .auth import AuthConfig
from .postgres import PostgresConfig
from .redis import RedisConfig
from .s3 import S3Config
from .server import ServerConfig


class AppConfig(BaseModel):
    postgres: PostgresConfig = Field(default_factory=PostgresConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    s3: S3Config = Field(default_factory=S3Config)
