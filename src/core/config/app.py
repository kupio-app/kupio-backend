from pydantic import BaseModel, Field

from .auth import AuthConfig
from .postgres import PostgresConfig
from .redis import RedisConfig
from .server import ServerConfig
from .stripe import StripeConfig


class AppConfig(BaseModel):
    postgres: PostgresConfig = Field(default_factory=PostgresConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    stripe: StripeConfig = Field(default_factory=StripeConfig)
