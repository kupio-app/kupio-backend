from pydantic import BaseModel

from .postgres import PostgresConfig
from .redis import RedisConfig
from .server import ServerConfig


class AppConfig(BaseModel):
    postgres: PostgresConfig = PostgresConfig()
    redis: RedisConfig = RedisConfig()
    server: ServerConfig = ServerConfig()
