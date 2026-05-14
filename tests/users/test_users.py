import src.domains.auth.service as auth_service
from sqlalchemy import inspect

from src.core.database.repositories import Repositories
from tests.helpers.auth import auth_header, register_payload

_auth_header = auth_header
_register_payload = register_payload


def _google_claims(*, sub: str, email: str) -> auth_service.GoogleIdTokenClaims:
    return {
        "sub": sub,
        "email": email,
        "email_verified": True,
        "given_name": "Google",
        "family_name": "User",
        "picture": "https://example.com/avatar.png",
    }


async def test_malformed_auth_header_returns_401(client):
    response = await client.get(
        "/api/users/me",
        headers={"Authorization": "invalid-header"},
    )
    assert response.status_code == 401


async def test_me_without_token_returns_401(client):
    response = await client.get("/api/users/me")
    assert response.status_code == 401


async def test_get_user_by_username_returns_public_profile(client):
    register = await client.post(
        "/api/auth/register",
        json=_register_payload(
            email="users1@example.com",
            username="users1",
            device_id="users-device-1",
        ),
    )
    assert register.status_code == 201

    response = await client.get("/api/users/users1")
    assert response.status_code == 200

    body = response.json()
    assert body["username"] == "users1"
    assert "email" not in body
    assert "role" not in body


async def test_get_user_by_username_returns_404_when_missing(client):
    response = await client.get("/api/users/missing-user")
    assert response.status_code == 404


async def test_me_returns_current_user(client):
    register = await client.post(
        "/api/auth/register",
        json=_register_payload(
            email="users2@example.com",
            username="users2",
            device_id="users-device-2",
        ),
    )
    assert register.status_code == 201
    access_token = register.json()["access_token"]

    me = await client.get("/api/users/me", headers=_auth_header(access_token))
    assert me.status_code == 200
    body = me.json()
    assert body["email"] == "users2@example.com"
    assert body["username"] == "users2"


async def test_update_profile_returns_401_without_token(client):
    response = await client.patch(
        "/api/users/me/profile",
        json={"first_name": "Alex"},
    )
    assert response.status_code == 401


async def test_update_profile_updates_display_name(client):
    register = await client.post(
        "/api/auth/register",
        json=_register_payload(
            email="users3@example.com",
            username="users3",
            device_id="users-device-3",
        ),
    )
    assert register.status_code == 201
    access_token = register.json()["access_token"]

    response = await client.patch(
        "/api/users/me/profile",
        headers=_auth_header(access_token),
        json={"first_name": "John", "last_name": "Doe"},
    )
    assert response.status_code == 200

    body = response.json()
    assert body["username"] == "users3"
    assert body["display_name"] == "John Doe"


async def test_update_profile_phone_conflict_returns_409(client):
    user_a = await client.post(
        "/api/auth/register",
        json=_register_payload(
            email="users4a@example.com",
            username="users4a",
            device_id="users-device-4a",
        ),
    )
    user_b = await client.post(
        "/api/auth/register",
        json=_register_payload(
            email="users4b@example.com",
            username="users4b",
            device_id="users-device-4b",
        ),
    )
    assert user_a.status_code == 201
    assert user_b.status_code == 201

    token_a = user_a.json()["access_token"]
    token_b = user_b.json()["access_token"]

    set_phone_a = await client.patch(
        "/api/users/me/profile",
        headers=_auth_header(token_a),
        json={"phone": "+12025550111"},
    )
    assert set_phone_a.status_code == 200

    set_phone_b = await client.patch(
        "/api/users/me/profile",
        headers=_auth_header(token_b),
        json={"phone": "+12025550111"},
    )
    assert set_phone_b.status_code == 409


async def test_set_username_for_google_user(client, monkeypatch):
    async def mock_verify_google_id_token(token: str, *, client_ids: list[str]):
        assert token == "google-token-users-1"
        assert client_ids == ["test-google-client-id"]
        return _google_claims(
            sub="google-users-sub-1",
            email="users-google@example.com",
        )

    monkeypatch.setattr(
        auth_service,
        "verify_google_id_token",
        mock_verify_google_id_token,
    )

    google_login = await client.post(
        "/api/auth/google",
        json={"id_token": "google-token-users-1", "device_id": "users-google-device-1"},
    )
    assert google_login.status_code == 200
    access_token = google_login.json()["access_token"]

    set_username = await client.patch(
        "/api/users/me/username",
        headers=_auth_header(access_token),
        json={"username": "users-google"},
    )
    assert set_username.status_code == 200

    body = set_username.json()
    assert body["username"] == "users-google"
    assert body["needs_username"] is False

    public_user = await client.get("/api/users/users-google")
    assert public_user.status_code == 200
    assert public_user.json()["username"] == "users-google"


async def test_set_username_rejects_second_change(client, monkeypatch):
    async def mock_verify_google_id_token(token: str, *, client_ids: list[str]):
        assert token == "google-token-users-2"
        assert client_ids == ["test-google-client-id"]
        return _google_claims(
            sub="google-users-sub-2",
            email="users-google-2@example.com",
        )

    monkeypatch.setattr(
        auth_service,
        "verify_google_id_token",
        mock_verify_google_id_token,
    )

    google_login = await client.post(
        "/api/auth/google",
        json={"id_token": "google-token-users-2", "device_id": "users-google-device-2"},
    )
    assert google_login.status_code == 200
    access_token = google_login.json()["access_token"]

    first = await client.patch(
        "/api/users/me/username",
        headers=_auth_header(access_token),
        json={"username": "users-google-2"},
    )
    assert first.status_code == 200

    second = await client.patch(
        "/api/users/me/username",
        headers=_auth_header(access_token),
        json={"username": "users-google-2b"},
    )
    assert second.status_code == 400


async def test_users_repository_separates_lean_and_response_reads(session_factory):
    async with session_factory() as session:
        repos = Repositories.from_session(session)
        user = await repos.users.create(
            email="repo-user@example.com",
            username="repo-user",
            password_hash="hash",
        )
        image = await repos.images.create(
            s3_key="users/repo-user/avatar/test.png",
            content_type="image/png",
            size_bytes=123,
        )
        user.avatar_image_id = image.id
        await session.commit()

    async with session_factory() as session:
        repos = Repositories.from_session(session)
        lean_user = await repos.users.get_by_id(user.id)
        assert lean_user is not None
        assert "avatar_image" in inspect(lean_user).unloaded

    async with session_factory() as session:
        repos = Repositories.from_session(session)
        response_user = await repos.users.get_for_response_by_id(user.id)
        assert response_user is not None
        assert "avatar_image" not in inspect(response_user).unloaded
