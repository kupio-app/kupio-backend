def _auth_header(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def _register_payload(*, email: str, username: str, device_id: str) -> dict[str, str]:
    return {
        "email": email,
        "username": username,
        "password": "strong-password",
        "device_id": device_id,
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
