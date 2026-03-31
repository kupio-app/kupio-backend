from __future__ import annotations

import asyncio
import time
import aiohttp

from typing import NotRequired, TypedDict, Any
from jose import JWTError, ExpiredSignatureError, jwt

from src.domains.auth.exceptions import InvalidGoogleTokenError

_GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
_GOOGLE_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}
_GOOGLE_JWKS_DEFAULT_TTL = 3600  # defensive fallback


class GoogleIdTokenClaims(TypedDict):
    sub: str
    email: str
    email_verified: bool
    given_name: NotRequired[str]
    family_name: NotRequired[str]
    picture: NotRequired[str]


class _GoogleJwksCache:
    def __init__(self) -> None:
        self._keys_by_kid: dict[str, dict[str, Any]] = {}
        self._expires_at: float = 0.0
        self._lock = asyncio.Lock()

    async def get_key(self, kid: str) -> dict[str, Any] | None:
        if self._is_fresh() and kid in self._keys_by_kid:
            return self._keys_by_kid[kid]

        async with self._lock:
            if self._is_fresh() and kid in self._keys_by_kid:
                return self._keys_by_kid[kid]

            await self._refresh()
            return self._keys_by_kid.get(kid)

    def _is_fresh(self) -> bool:
        return time.monotonic() < self._expires_at and bool(self._keys_by_kid)

    async def _refresh(self) -> None:
        keys_by_kid, ttl_seconds = await _fetch_google_jwks()
        self._keys_by_kid = keys_by_kid
        self._expires_at = time.monotonic() + ttl_seconds


_jwks_cache = _GoogleJwksCache()


async def verify_google_id_token(
    token: str,
    *,
    client_ids: list[str],
) -> GoogleIdTokenClaims:
    if not client_ids:
        raise InvalidGoogleTokenError()
    try:
        header = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise InvalidGoogleTokenError() from exc

    kid = header.get("kid")
    algorithm = header.get("alg")
    if not isinstance(kid, str) or algorithm != "RS256":
        raise InvalidGoogleTokenError()

    key = await _jwks_cache.get_key(kid)
    if key is None:
        raise InvalidGoogleTokenError()

    try:
        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            options={"verify_aud": False, "verify_iss": False},
        )
    except (ExpiredSignatureError, JWTError) as exc:
        raise InvalidGoogleTokenError() from exc

    required = ("sub", "email", "email_verified")
    if any(key not in claims for key in required):
        raise InvalidGoogleTokenError()
    if not _audience_matches(claims.get("aud"), client_ids):
        raise InvalidGoogleTokenError()
    if claims.get("iss") not in _GOOGLE_ISSUERS:
        raise InvalidGoogleTokenError()

    return GoogleIdTokenClaims(
        sub=claims["sub"],
        email=claims["email"],
        email_verified=bool(claims["email_verified"]),
        given_name=claims.get("given_name"),
        family_name=claims.get("family_name"),
        picture=claims.get("picture"),
    )


async def _fetch_google_jwks() -> tuple[dict[str, dict[str, Any]], int]:
    try:
        timeout = aiohttp.ClientTimeout(total=5.0)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(_GOOGLE_JWKS_URL) as response:
                if response.status >= 400:
                    raise InvalidGoogleTokenError()
                payload = await response.json()
                cache_control = response.headers.get("Cache-Control")
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as exc:
        raise InvalidGoogleTokenError() from exc

    keys = payload.get("keys")
    if not isinstance(keys, list):
        raise InvalidGoogleTokenError()

    keys_by_kid = {
        key["kid"]: key
        for key in keys
        if isinstance(key, dict) and isinstance(key.get("kid"), str)
    }
    if not keys_by_kid:
        raise InvalidGoogleTokenError()

    return keys_by_kid, _parse_max_age(cache_control)


def _parse_max_age(cache_control: str | None) -> int:
    if not cache_control:  # fallback
        return _GOOGLE_JWKS_DEFAULT_TTL

    for directive in cache_control.split(","):
        directive = directive.strip()
        if directive.startswith("max-age="):
            _, _, value = directive.partition("=")
            if value.isdigit():
                return int(value)

    return _GOOGLE_JWKS_DEFAULT_TTL


def _audience_matches(aud_claim: Any, client_ids: list[str]) -> bool:
    if isinstance(aud_claim, str):
        return aud_claim in client_ids
    if isinstance(aud_claim, list):
        return any(isinstance(item, str) and item in client_ids for item in aud_claim)
    return False
