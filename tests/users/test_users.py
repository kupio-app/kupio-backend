async def test_malformed_auth_header_returns_401(client):
    response = await client.get(
        "/api/users/me",
        headers={"Authorization": "invalid-header"},
    )
    assert response.status_code == 401


async def test_me_without_token_returns_401(client):
    response = await client.get("/api/users/me")
    assert response.status_code == 401
