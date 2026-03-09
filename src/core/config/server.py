from .base import EnvSettings


class PostgresConfig(EnvSettings, env_prefix="POSTGRES"):
    host: str = "localhost"
    port: int = 9988
    reload: bool = False
