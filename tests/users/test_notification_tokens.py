"""Tests for POST /api/users/me/notification-tokens.

NotificationTokensRepository.upsert uses a PostgreSQL-specific ON CONFLICT clause.
The tests patch it with a SQLite-compatible implementation so the rest of the
stack (auth, routing, service) runs through the real code path.
"""

import datetime
import uuid

import pytest_asyncio
from sqlalchemy import select

from src.domains.users.models import NotificationToken
from src.domains.users.repository import NotificationTokensRepository
from tests.helpers.auth import auth_header, register_user


async def _sqlite_upsert(
    self: NotificationTokensRepository,
    *,
    user_id: uuid.UUID,
    token: str,
    platform,
    device_id: str | None = None,
) -> NotificationToken:
    now = datetime.datetime.now(datetime.UTC)
    existing = await self.session.scalar(
        select(NotificationToken).where(
            NotificationToken.user_id == user_id,
            NotificationToken.platform == platform,
            NotificationToken.token == token,
        )
    )
    if existing is not None:
        existing.last_seen_at = now
        await self.session.flush()
        return existing
    return await self._add(
        NotificationToken,
        user_id=user_id,
        token=token,
        platform=platform,
        last_seen_at=now,
        device_id=device_id,
    )


@pytest_asyncio.fixture(autouse=True)
async def patch_notification_token_upsert(monkeypatch):
    monkeypatch.setattr(NotificationTokensRepository, "upsert", _sqlite_upsert)


def _auth_header(token: str) -> dict:
    return auth_header(token)


async def _register(
    client, *, email: str, username: str, device_id: str = "device"
) -> str:
    data = await register_user(
        client, email=email, username=username, device_id=device_id
    )
    return data["access_token"]


async def test_register_notification_token_returns_201(client):
    token = await _register(client, email="dt1@example.com", username="dt1")

    resp = await client.post(
        "/api/users/me/notification-tokens",
        headers=_auth_header(token),
        json={"token": "fcm-token-abc123", "platform": "android"},
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["platform"] == "android"
    assert "id" in body
    assert "last_seen_at" in body


async def test_register_notification_token_response_structure(client):
    token = await _register(client, email="dt2@example.com", username="dt2")

    resp = await client.post(
        "/api/users/me/notification-tokens",
        headers=_auth_header(token),
        json={"token": "fcm-token-ios-xyz", "platform": "ios"},
    )

    assert resp.status_code == 201
    body = resp.json()
    assert set(body.keys()) >= {"id", "platform", "last_seen_at"}
    assert body["platform"] == "ios"
    uuid.UUID(body["id"])  # must be a valid UUID


async def test_register_notification_token_idempotent_updates_last_seen(client):
    """Registering the same (user, platform, token) tuple twice should not
    create a second row — it should update last_seen_at instead."""
    token = await _register(client, email="dt3@example.com", username="dt3")
    payload = {"token": "same-fcm-token", "platform": "android"}

    first = await client.post(
        "/api/users/me/notification-tokens",
        headers=_auth_header(token),
        json=payload,
    )
    assert first.status_code == 201
    first_id = first.json()["id"]
    first_seen = first.json()["last_seen_at"]

    second = await client.post(
        "/api/users/me/notification-tokens",
        headers=_auth_header(token),
        json=payload,
    )
    assert second.status_code == 201
    assert second.json()["id"] == first_id
    assert second.json()["last_seen_at"] >= first_seen


async def test_register_notification_token_different_platforms_are_separate(client):
    """Same token string on different platforms should be stored independently."""
    token = await _register(client, email="dt4@example.com", username="dt4")

    ios_resp = await client.post(
        "/api/users/me/notification-tokens",
        headers=_auth_header(token),
        json={"token": "apns-token-xyz", "platform": "ios"},
    )
    android_resp = await client.post(
        "/api/users/me/notification-tokens",
        headers=_auth_header(token),
        json={"token": "apns-token-xyz", "platform": "android"},
    )

    assert ios_resp.status_code == 201
    assert android_resp.status_code == 201
    assert ios_resp.json()["id"] != android_resp.json()["id"]


async def test_register_notification_token_requires_auth(client):
    resp = await client.post(
        "/api/users/me/notification-tokens",
        json={"token": "fcm-token", "platform": "android"},
    )

    assert resp.status_code == 401


async def test_register_notification_token_empty_token_returns_422(client):
    token = await _register(client, email="dt6@example.com", username="dt6")

    resp = await client.post(
        "/api/users/me/notification-tokens",
        headers=_auth_header(token),
        json={"token": "", "platform": "android"},
    )

    assert resp.status_code == 422


async def test_register_notification_token_invalid_platform_returns_422(client):
    token = await _register(client, email="dt7@example.com", username="dt7")

    resp = await client.post(
        "/api/users/me/notification-tokens",
        headers=_auth_header(token),
        json={"token": "fcm-token-abc", "platform": "windows"},
    )

    assert resp.status_code == 422


async def test_register_notification_token_missing_platform_returns_422(client):
    token = await _register(client, email="dt8@example.com", username="dt8")

    resp = await client.post(
        "/api/users/me/notification-tokens",
        headers=_auth_header(token),
        json={"token": "fcm-token-abc"},
    )

    assert resp.status_code == 422


async def test_register_notification_token_token_too_long_returns_422(client):
    token = await _register(client, email="dt9@example.com", username="dt9")

    resp = await client.post(
        "/api/users/me/notification-tokens",
        headers=_auth_header(token),
        json={"token": "x" * 513, "platform": "ios"},
    )

    assert resp.status_code == 422
