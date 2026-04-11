from pydantic import SecretStr

from .base import EnvSettings


class StripeConfig(EnvSettings, env_prefix="STRIPE__"):
    secret_key: SecretStr
    webhook_secret: SecretStr
    success_url: str
    cancel_url: str
