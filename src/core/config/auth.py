from pydantic import SecretStr

from .base import EnvSettings


class AuthConfig(EnvSettings, env_prefix="AUTH__"):
    jwt_secret: SecretStr = SecretStr("supersecret")
    jwt_algorithm: str = "HS256"
    access_ttl: int = 15  # in minutes
    refresh_ttl: int = 7  # in days
    not_validate_exp: bool = (
        False  # For testing purposes, disable expiration validation
    )
