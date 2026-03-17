import uuid


def _auth_header(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def _register_payload(*, email: str, username: str, device_id: str) -> dict[str, str]:
    return {
        "email": email,
        "username": username,
        "password": "strong-password",
        "device_id": device_id,
    }


async def test_register_and_me(client):
    response = await client.post(
        "/api/auth/register",
        json=_register_payload(
            email="user1@example.com",
            username="user1",
            device_id="phone-1",
        ),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]

    me = await client.get("/api/auth/me", headers=_auth_header(body["access_token"]))
    assert me.status_code == 200
    me_body = me.json()["user"]
    assert me_body["email"] == "user1@example.com"
    assert me_body["username"] == "user1"


async def test_login_and_sessions_list(client):
    await client.post(
        "/api/auth/register",
        json=_register_payload(
            email="user2@example.com",
            username="user2",
            device_id="web-1",
        ),
    )

    login = await client.post(
        "/api/auth/login",
        json={
            "email": "user2@example.com",
            "password": "strong-password",
            "device_id": "laptop-1",
        },
    )
    assert login.status_code == 200
    access_token = login.json()["access_token"]

    sessions = await client.get(
        "/api/auth/sessions",
        headers=_auth_header(access_token),
    )
    assert sessions.status_code == 200
    sessions_body = sessions.json()["sessions"]
    assert len(sessions_body) == 2
    assert {s["device_id"] for s in sessions_body} == {"web-1", "laptop-1"}


async def test_refresh_rotates_token(client):
    register = await client.post(
        "/api/auth/register",
        json=_register_payload(
            email="user3@example.com",
            username="user3",
            device_id="tablet-1",
        ),
    )
    old_refresh = register.json()["refresh_token"]

    refresh = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": old_refresh, "device_id": "tablet-1"},
    )

    assert refresh.status_code == 200
    new_refresh = refresh.json()["refresh_token"]
    assert new_refresh != old_refresh

    reuse_old = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": old_refresh, "device_id": "tablet-1"},
    )
    assert reuse_old.status_code == 401


async def test_revoke_one_and_all_sessions(client):
    register = await client.post(
        "/api/auth/register",
        json=_register_payload(
            email="user4@example.com",
            username="user4",
            device_id="phone-4",
        ),
    )
    access_token = register.json()["access_token"]

    await client.post(
        "/api/auth/login",
        json={
            "email": "user4@example.com",
            "password": "strong-password",
            "device_id": "desktop-4",
        },
    )

    sessions = await client.get(
        "/api/auth/sessions",
        headers=_auth_header(access_token),
    )
    sessions_list = sessions.json()["sessions"]
    assert len(sessions_list) == 2

    session_id = sessions_list[0]["id"]
    revoke_one = await client.delete(
        f"/api/auth/sessions/{session_id}",
        headers=_auth_header(access_token),
    )
    assert revoke_one.status_code == 204

    after_one = await client.get(
        "/api/auth/sessions",
        headers=_auth_header(access_token),
    )
    assert len(after_one.json()["sessions"]) == 1

    revoke_all = await client.delete(
        "/api/auth/sessions",
        headers=_auth_header(access_token),
    )
    assert revoke_all.status_code == 204

    after_all = await client.get(
        "/api/auth/sessions",
        headers=_auth_header(access_token),
    )
    assert after_all.status_code == 200
    assert after_all.json()["sessions"] == []


async def test_revoke_unknown_session_returns_404(client):
    register = await client.post(
        "/api/auth/register",
        json=_register_payload(
            email="user5@example.com",
            username="user5",
            device_id="phone-5",
        ),
    )
    access_token = register.json()["access_token"]

    response = await client.delete(
        f"/api/auth/sessions/{uuid.uuid4()}",
        headers=_auth_header(access_token),
    )

    assert response.status_code == 404


async def test_register_duplicate_email_returns_409(client):
    first = await client.post(
        "/api/auth/register",
        json=_register_payload(
            email="dup@example.com",
            username="dup-user-1",
            device_id="dup-device-1",
        ),
    )
    assert first.status_code == 201

    second = await client.post(
        "/api/auth/register",
        json=_register_payload(
            email="dup@example.com",
            username="dup-user-2",
            device_id="dup-device-2",
        ),
    )
    assert second.status_code == 409


async def test_login_invalid_credentials_returns_401(client):
    await client.post(
        "/api/auth/register",
        json=_register_payload(
            email="user6@example.com",
            username="user6",
            device_id="phone-6",
        ),
    )

    login = await client.post(
        "/api/auth/login",
        json={
            "email": "user6@example.com",
            "password": "wrong-password",
            "device_id": "phone-6",
        },
    )
    assert login.status_code == 401


async def test_me_without_token_returns_401(client):
    response = await client.get("/api/auth/me")
    assert response.status_code == 401


async def test_refresh_with_wrong_device_id_returns_401(client):
    register = await client.post(
        "/api/auth/register",
        json=_register_payload(
            email="user7@example.com",
            username="user7",
            device_id="phone-7",
        ),
    )
    refresh_token = register.json()["refresh_token"]

    refresh = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh_token, "device_id": "other-device"},
    )
    assert refresh.status_code == 401


async def test_revoke_foreign_session_returns_404(client):
    user_a = await client.post(
        "/api/auth/register",
        json=_register_payload(
            email="user8a@example.com",
            username="user8a",
            device_id="phone-8a",
        ),
    )
    token_a = user_a.json()["access_token"]

    user_b = await client.post(
        "/api/auth/register",
        json=_register_payload(
            email="user8b@example.com",
            username="user8b",
            device_id="phone-8b",
        ),
    )
    token_b = user_b.json()["access_token"]

    sessions_a = await client.get(
        "/api/auth/sessions",
        headers=_auth_header(token_a),
    )
    foreign_session_id = sessions_a.json()["sessions"][0]["id"]

    revoke = await client.delete(
        f"/api/auth/sessions/{foreign_session_id}",
        headers=_auth_header(token_b),
    )
    assert revoke.status_code == 404
