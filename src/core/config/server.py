from .base import EnvSettings


class ServerConfig(EnvSettings, env_prefix="SERVER__"):
    host: str = "localhost"
    port: int = 9988
    reload: bool = False
    debug: bool = False
