from .base import EnvSettings
from .postgres import PostgresConfig
from .redis import RedisConfig


class AppConfig(EnvSettings, env_prefix="KUPIO"):
    postgres: PostgresConfig
    redis: RedisConfig

    debug: bool = False
