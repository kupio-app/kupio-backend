from typing import Any


def auth_header(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def register_payload(*, email: str, username: str, device_id: str) -> dict[str, str]:
    return {
        "email": email,
        "username": username,
        "password": "strong-password",
        "device_id": device_id,
    }


async def register_user(
    client,
    *,
    email: str,
    username: str,
    device_id: str = "device",
    password: str = "strong-password",
) -> dict[str, Any]:
    resp = await client.post(
        "/api/auth/register",
        json={
            "email": email,
            "username": username,
            "password": password,
            "device_id": device_id,
        },
    )
    assert resp.status_code == 201
    return resp.json()


async def login_user(
    client,
    *,
    email: str,
    password: str = "strong-password",
    device_id: str = "device",
) -> dict[str, Any]:
    resp = await client.post(
        "/api/auth/login",
        json={
            "email": email,
            "password": password,
            "device_id": device_id,
        },
    )
    assert resp.status_code == 200
    return resp.json()
