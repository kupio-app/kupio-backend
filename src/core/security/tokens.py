import secrets
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from jose import jwt

from src.core.config import AuthConfig


def generate_refresh_token() -> str:
    """Cryptographically secure random string for refresh token"""
    return secrets.token_urlsafe(64)


def create_access_token(user_id: str, config: AuthConfig) -> tuple[str, str]:
    """
    Create JWT access token with user_id and expiration

    :return: (token, jti)
    """
    expire_at = datetime.now(UTC) + timedelta(minutes=config.access_ttl)
    jti = str(uuid4())
    token = jwt.encode(
        {
            "sub": user_id,
            "exp": int(expire_at.timestamp()),
            "jti": jti,  # For blacklisting if needed in future
        },
        config.jwt_secret.get_secret_value(),
        algorithm=config.jwt_algorithm,
    )

    return token, jti


def decode_access_token(token: str, config: AuthConfig) -> str:
    """
    Return user_id from token or raise if invalid/expired

    :return user_id: str
    :raises: jwt.ExpiredSignatureError, jwt.JWTError
    """
    payload = jwt.decode(
        token, config.jwt_secret.get_secret_value(), algorithms=[config.jwt_algorithm]
    )
    return payload["sub"]
