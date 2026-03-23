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


async def test_register_duplicate_username_returns_409(client):
    first = await client.post(
        "/api/auth/register",
        json=_register_payload(
            email="user9a@example.com",
            username="dup-username",
            device_id="dup-device-username-1",
        ),
    )
    assert first.status_code == 201

    second = await client.post(
        "/api/auth/register",
        json=_register_payload(
            email="user9b@example.com",
            username="dup-username",
            device_id="dup-device-username-2",
        ),
    )
    assert second.status_code == 409


async def test_register_password_too_short_returns_422(client):
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "user10@example.com",
            "username": "user10",
            "password": "short",  # Less than 8 characters
            "device_id": "phone-10",
        },
    )
    assert response.status_code == 422


async def test_register_password_too_long_returns_422(client):
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "user11@example.com",
            "username": "user11",
            "password": "x" * 129,  # More than 128 characters
            "device_id": "phone-11",
        },
    )
    assert response.status_code == 422


async def test_register_username_too_short_returns_422(client):
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "user12@example.com",
            "username": "ab",  # Less than 3 characters
            "password": "strong-password",
            "device_id": "phone-12",
        },
    )
    assert response.status_code == 422


async def test_register_username_too_long_returns_422(client):
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "user13@example.com",
            "username": "x" * 51,  # More than 50 characters
            "password": "strong-password",
            "device_id": "phone-13",
        },
    )
    assert response.status_code == 422


async def test_register_username_with_special_chars_returns_422(client):
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "user14@example.com",
            "username": "user@special#chars!",
            "password": "strong-password",
            "device_id": "phone-14",
        },
    )
    assert response.status_code == 422


async def test_register_invalid_email_returns_422(client):
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "not-an-email",
            "username": "user15",
            "password": "strong-password",
            "device_id": "phone-15",
        },
    )
    assert response.status_code == 422


async def test_login_nonexistent_user_returns_401(client):
    response = await client.post(
        "/api/auth/login",
        json={
            "email": "nonexistent@example.com",
            "password": "strong-password",
            "device_id": "phone",
        },
    )
    assert response.status_code == 401


async def test_logout_invalidates_session(client):
    register = await client.post(
        "/api/auth/register",
        json=_register_payload(
            email="user16@example.com",
            username="user16",
            device_id="phone-16",
        ),
    )
    refresh_token = register.json()["refresh_token"]

    # Logout
    logout = await client.post(
        "/api/auth/logout",
        json={"refresh_token": refresh_token},
    )
    assert logout.status_code == 202

    # Try to refresh with the revoked token
    refresh = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh_token, "device_id": "phone-16"},
    )
    assert refresh.status_code == 401


async def test_multiple_devices_same_user(client):
    register = await client.post(
        "/api/auth/register",
        json=_register_payload(
            email="user17@example.com",
            username="user17",
            device_id="phone-17",
        ),
    )
    first_token = register.json()["access_token"]

    # Login with second device
    login_second = await client.post(
        "/api/auth/login",
        json={
            "email": "user17@example.com",
            "password": "strong-password",
            "device_id": "tablet-17",
        },
    )
    assert login_second.status_code == 200
    second_token = login_second.json()["access_token"]

    # Login with third device
    login_third = await client.post(
        "/api/auth/login",
        json={
            "email": "user17@example.com",
            "password": "strong-password",
            "device_id": "laptop-17",
        },
    )
    assert login_third.status_code == 200

    # Check sessions list
    sessions = await client.get(
        "/api/auth/sessions",
        headers=_auth_header(first_token),
    )
    assert sessions.status_code == 200
    sessions_list = sessions.json()["sessions"]
    assert len(sessions_list) == 3
    device_ids = {s["device_id"] for s in sessions_list}
    assert device_ids == {"phone-17", "tablet-17", "laptop-17"}


async def test_login_same_device_revokes_previous_session(client):
    register = await client.post(
        "/api/auth/register",
        json=_register_payload(
            email="user18@example.com",
            username="user18",
            device_id="phone-18",
        ),
    )
    first_refresh = register.json()["refresh_token"]

    # Login again with the same device
    login_again = await client.post(
        "/api/auth/login",
        json={
            "email": "user18@example.com",
            "password": "strong-password",
            "device_id": "phone-18",
        },
    )
    assert login_again.status_code == 200
    second_refresh = login_again.json()["refresh_token"]

    # First refresh token should be invalid now
    refresh_old = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": first_refresh, "device_id": "phone-18"},
    )
    assert refresh_old.status_code == 401

    # Second refresh token should work
    refresh_new = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": second_refresh, "device_id": "phone-18"},
    )
    assert refresh_new.status_code == 200


async def test_tokens_response_structure(client):
    response = await client.post(
        "/api/auth/register",
        json=_register_payload(
            email="user21@example.com",
            username="user21",
            device_id="phone-21",
        ),
    )
    assert response.status_code == 201

    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert "access_expires_at" in body
    assert "refresh_expires_at" in body
    assert body["token_type"] == "bearer"
    assert isinstance(body["access_expires_at"], int)
    assert isinstance(body["refresh_expires_at"], int)
    assert body["access_expires_at"] > 0
    assert body["refresh_expires_at"] > 0


async def test_malformed_auth_header_returns_401(client):
    response = await client.get(
        "/api/auth/me",
        headers={"Authorization": "invalid-header"},
    )
    assert response.status_code == 401


async def test_sessions_do_not_include_revoked(client):
    register = await client.post(
        "/api/auth/register",
        json=_register_payload(
            email="user23@example.com",
            username="user23",
            device_id="phone-23",
        ),
    )
    access_token = register.json()["access_token"]

    # Create a second session
    await client.post(
        "/api/auth/login",
        json={
            "email": "user23@example.com",
            "password": "strong-password",
            "device_id": "tablet-23",
        },
    )

    # Get sessions and revoke one
    sessions = await client.get(
        "/api/auth/sessions",
        headers=_auth_header(access_token),
    )
    sessions_list = sessions.json()["sessions"]
    assert len(sessions_list) == 2

    session_to_revoke = sessions_list[0]
    revoke = await client.delete(
        f"/api/auth/sessions/{session_to_revoke['id']}",
        headers=_auth_header(access_token),
    )
    assert revoke.status_code == 204

    # List sessions again
    sessions_after = await client.get(
        "/api/auth/sessions",
        headers=_auth_header(access_token),
    )
    sessions_after_list = sessions_after.json()["sessions"]
    assert len(sessions_after_list) == 1

    # Ensure revoked session is not in the list
    revoked_ids = [s["id"] for s in sessions_after_list]
    assert str(session_to_revoke["id"]) not in [str(id) for id in revoked_ids]


async def test_change_password_revokes_all_sessions_and_returns_new_session(client):
    register = await client.post(
        "/api/auth/register",
        json=_register_payload(
            email="user24@example.com",
            username="user24",
            device_id="phone-24",
        ),
    )
    assert register.status_code == 201
    old_access = register.json()["access_token"]
    old_refresh_phone = register.json()["refresh_token"]

    login = await client.post(
        "/api/auth/login",
        json={
            "email": "user24@example.com",
            "password": "strong-password",
            "device_id": "laptop-24",
        },
    )
    assert login.status_code == 200
    old_refresh_laptop = login.json()["refresh_token"]

    changed = await client.post(
        "/api/auth/change-password",
        headers=_auth_header(old_access),
        json={
            "current_password": "strong-password",
            "new_password": "new-strong-password",
            "device_id": "password-reset-24",
        },
    )
    assert changed.status_code == 200
    new_refresh = changed.json()["refresh_token"]

    refresh_old_phone = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": old_refresh_phone, "device_id": "phone-24"},
    )
    assert refresh_old_phone.status_code == 401

    refresh_old_laptop = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": old_refresh_laptop, "device_id": "laptop-24"},
    )
    assert refresh_old_laptop.status_code == 401

    refresh_new = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": new_refresh, "device_id": "password-reset-24"},
    )
    assert refresh_new.status_code == 200

    login_with_old_password = await client.post(
        "/api/auth/login",
        json={
            "email": "user24@example.com",
            "password": "strong-password",
            "device_id": "old-password-device-24",
        },
    )
    assert login_with_old_password.status_code == 401

    login_with_new_password = await client.post(
        "/api/auth/login",
        json={
            "email": "user24@example.com",
            "password": "new-strong-password",
            "device_id": "new-password-device-24",
        },
    )
    assert login_with_new_password.status_code == 200


async def test_change_password_with_invalid_current_password_returns_401(client):
    register = await client.post(
        "/api/auth/register",
        json=_register_payload(
            email="user25@example.com",
            username="user25",
            device_id="phone-25",
        ),
    )
    assert register.status_code == 201
    access_token = register.json()["access_token"]
    refresh_token = register.json()["refresh_token"]

    changed = await client.post(
        "/api/auth/change-password",
        headers=_auth_header(access_token),
        json={
            "current_password": "wrong-password",
            "new_password": "new-strong-password",
            "device_id": "password-reset-25",
        },
    )
    assert changed.status_code == 401

    refresh_still_valid = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh_token, "device_id": "phone-25"},
    )
    assert refresh_still_valid.status_code == 200


async def test_change_password_with_same_new_password_returns_400(client):
    register = await client.post(
        "/api/auth/register",
        json=_register_payload(
            email="user26@example.com",
            username="user26",
            device_id="phone-26",
        ),
    )
    assert register.status_code == 201

    response = await client.post(
        "/api/auth/change-password",
        headers=_auth_header(register.json()["access_token"]),
        json={
            "current_password": "strong-password",
            "new_password": "strong-password",
            "device_id": "password-reset-26",
        },
    )
    assert response.status_code == 400
