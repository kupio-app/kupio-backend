from pydantic import SecretStr

from src.core.config.base import EnvSettings


class S3Config(EnvSettings, env_prefix="S3__"):
    bucket: str
    region: str
    access_key_id: str
    secret_access_key: SecretStr
