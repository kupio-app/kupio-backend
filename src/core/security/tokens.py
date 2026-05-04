import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from jose import jwt

from src.core.config import AuthConfig


def hash_refresh_token(refresh_token: str) -> str:
    return hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()


def generate_refresh_token(config: AuthConfig) -> tuple[str, datetime]:
    """
    Cryptographically secure random string for refresh token and expiration time

    :return: (token, expire_at)
    """
    expires_at = datetime.now(UTC) + timedelta(days=config.refresh_ttl)

    return secrets.token_urlsafe(64), expires_at


def create_access_token(
    user_id: str, config: AuthConfig, device_id: str | None = None
) -> tuple[str, str, int]:
    """
    Create JWT access token with user_id and expiration

    :return: (token, jti, expires_at)
    """
    expires_at = datetime.now(UTC) + timedelta(minutes=config.access_ttl)
    expires_at = int(expires_at.timestamp())
    jti = str(uuid4())
    claims: dict = {
        "sub": user_id,
        "exp": expires_at,
        "jti": jti,  # For blacklisting if needed in future
    }
    if device_id is not None:
        claims["did"] = device_id
    token = jwt.encode(
        claims,
        config.jwt_secret.get_secret_value(),
        algorithm=config.jwt_algorithm,
    )

    return token, jti, expires_at


def decode_access_token(token: str, config: AuthConfig) -> tuple[str, str | None]:
    """
    Return (user_id, device_id) from token or raise if invalid/expired

    :return: (user_id, device_id)
    :raises: jwt.ExpiredSignatureError, jwt.JWTError
    """
    payload = jwt.decode(
        token,
        config.jwt_secret.get_secret_value(),
        algorithms=[config.jwt_algorithm],
        options={"verify_exp": not config.not_validate_exp},
    )
    return payload["sub"], payload.get("did")
