from .app import AppConfig
from .postgres import PostgresConfig
from .redis import RedisConfig

from functools import lru_cache


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    return AppConfig()
