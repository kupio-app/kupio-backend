from pydantic import BaseModel, Field

from .postgres import PostgresConfig
from .redis import RedisConfig
from .server import ServerConfig


class AppConfig(BaseModel):
    postgres: PostgresConfig = Field(default_factory=PostgresConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
