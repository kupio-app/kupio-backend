from unittest.mock import AsyncMock

import pytest

import src.core.security.google as google_security
from src.domains.auth.exceptions import InvalidGoogleTokenError


@pytest.mark.asyncio
async def test_verify_google_id_token_uses_cached_jwk(monkeypatch):
    cache = google_security._GoogleJwksCache()
    monkeypatch.setattr(google_security, "_jwks_cache", cache)
    monkeypatch.setattr(
        google_security.jwt,
        "get_unverified_header",
        lambda token: {"kid": "kid-1", "alg": "RS256"},
    )
    monkeypatch.setattr(
        google_security.jwt,
        "decode",
        lambda *args, **kwargs: {
            "sub": "sub-1",
            "email": "user@example.com",
            "email_verified": True,
            "aud": "client-1",
            "iss": "https://accounts.google.com",
        },
    )

    fetch_mock = AsyncMock(
        return_value=(
            {"kid-1": {"kid": "kid-1", "kty": "RSA", "n": "n", "e": "AQAB"}},
            3600,
        )
    )
    monkeypatch.setattr(google_security, "_fetch_google_jwks", fetch_mock)

    await google_security.verify_google_id_token("token-1", client_ids=["client-1"])
    await google_security.verify_google_id_token("token-2", client_ids=["client-1"])

    assert fetch_mock.await_count == 1


@pytest.mark.asyncio
async def test_verify_google_id_token_disables_at_hash_verification(monkeypatch):
    cache = google_security._GoogleJwksCache()
    monkeypatch.setattr(google_security, "_jwks_cache", cache)
    monkeypatch.setattr(
        google_security.jwt,
        "get_unverified_header",
        lambda token: {"kid": "kid-1", "alg": "RS256"},
    )

    def decode(*args, **kwargs):
        assert kwargs["options"]["verify_at_hash"] is False
        return {
            "sub": "sub-1",
            "email": "user@example.com",
            "email_verified": True,
            "aud": "client-1",
            "iss": "https://accounts.google.com",
            "at_hash": "ignored",
        }

    monkeypatch.setattr(google_security.jwt, "decode", decode)
    monkeypatch.setattr(
        google_security,
        "_fetch_google_jwks",
        AsyncMock(
            return_value=(
                {"kid-1": {"kid": "kid-1", "kty": "RSA", "n": "n", "e": "AQAB"}},
                3600,
            )
        ),
    )

    claims = await google_security.verify_google_id_token(
        "token-1",
        client_ids=["client-1"],
    )

    assert claims["email"] == "user@example.com"


@pytest.mark.asyncio
async def test_verify_google_id_token_rejects_unknown_audience(monkeypatch):
    cache = google_security._GoogleJwksCache()
    monkeypatch.setattr(google_security, "_jwks_cache", cache)
    monkeypatch.setattr(
        google_security.jwt,
        "get_unverified_header",
        lambda token: {"kid": "kid-1", "alg": "RS256"},
    )
    monkeypatch.setattr(
        google_security.jwt,
        "decode",
        lambda *args, **kwargs: {
            "sub": "sub-1",
            "email": "user@example.com",
            "email_verified": True,
            "aud": "other-client",
            "iss": "https://accounts.google.com",
        },
    )
    monkeypatch.setattr(
        google_security,
        "_fetch_google_jwks",
        AsyncMock(
            return_value=(
                {"kid-1": {"kid": "kid-1", "kty": "RSA", "n": "n", "e": "AQAB"}},
                3600,
            )
        ),
    )

    with pytest.raises(InvalidGoogleTokenError):
        await google_security.verify_google_id_token("token-1", client_ids=["client-1"])


@pytest.mark.asyncio
async def test_verify_google_id_token_rejects_non_rs256_header(monkeypatch):
    monkeypatch.setattr(
        google_security.jwt,
        "get_unverified_header",
        lambda token: {"kid": "kid-1", "alg": "HS256"},
    )

    with pytest.raises(InvalidGoogleTokenError):
        await google_security.verify_google_id_token("token-1", client_ids=["client-1"])


@pytest.mark.asyncio
async def test_fetch_google_jwks_wraps_transport_failures(monkeypatch):
    class FakeResponse:
        status = 200
        headers = {}

        async def json(self):
            raise ValueError("bad json")

    class FakeRequestContext:
        async def __aenter__(self):
            return FakeResponse()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeSession:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def get(self, url):
            return FakeRequestContext()

    monkeypatch.setattr(google_security.aiohttp, "ClientSession", FakeSession)

    with pytest.raises(InvalidGoogleTokenError):
        await google_security._fetch_google_jwks()
