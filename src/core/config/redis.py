from .base import EnvSettings


class RedisConfig(EnvSettings, env_prefix="REDIS"):
    host: str
    port: int
    db: int

    def build_url(self) -> str:
        return f"redis://{self.host}:{self.port}/{self.db}"
