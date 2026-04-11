from functools import lru_cache

from .app import AppConfig
from .auth import AuthConfig
from .firebase import FirebaseConfig
from .postgres import PostgresConfig
from .redis import RedisConfig
from .server import ServerConfig


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    return AppConfig()
