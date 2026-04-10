from functools import lru_cache

from .app import AppConfig
from .auth import AuthConfig
from .postgres import PostgresConfig
from .redis import RedisConfig
from .server import ServerConfig
from .stripe import StripeConfig


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    return AppConfig()


__all__ = [
    "get_config",
    "AppConfig",
    "AuthConfig",
    "PostgresConfig",
    "RedisConfig",
    "ServerConfig",
    "StripeConfig",
]
