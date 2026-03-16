from pydantic import SecretStr

from .base import EnvSettings


class AuthConfig(EnvSettings, env_prefix="AUTH__"):
    jwt_secret: SecretStr = SecretStr("supersecret")
    jwt_algorithm: str = "HS256"
    access_ttl_minutes: int = 15
    refresh_ttl_days: int = 7
