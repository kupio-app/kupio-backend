import uuid

from src.domains.categories.models import Category

from src.domains.filter_definitions.models import FilterDefinition
from src.domains.users.enums import UserRole
from src.domains.users.models import User
from tests.helpers.auth import auth_header, login_user, register_user
from tests.helpers.listings import create_category


def _auth_header(token: str) -> dict:
    return auth_header(token)


async def _register(client, *, email: str, username: str) -> str:
    data = await register_user(client, email=email, username=username)
    return data["access_token"]


async def _create_moderator(session_factory) -> None:
    from src.core.security import hash_password

    async with session_factory() as session:
        user = User(
            id=uuid.uuid4(),
            username="moderator",
            email="moderator@test.com",
            password_hash=hash_password("strong-password"),
            role=UserRole.MODERATOR,
        )
        session.add(user)
        await session.commit()


async def _login(client, *, email: str) -> str:
    data = await login_user(client, email=email, device_id="device")
    return data["access_token"]


async def _create_category(session_factory, *, name: str = "Electronics") -> Category:
    return await create_category(session_factory, name=name, depth=0)


def _filter_payload(**overrides) -> dict:
    base = {
        "slug": "ram",
        "label": "RAM",
        "filter_type": "select",
        "options": {"values": ["8 GB", "16 GB", "32 GB"]},
        "is_required": False,
        "display_order": 0,
    }
    return {**base, **overrides}


async def _create_filter(
    session_factory, *, category_id: int, **overrides
) -> FilterDefinition:
    async with session_factory() as session:
        filter_def = FilterDefinition(
            category_id=category_id, **_filter_payload(**overrides)
        )
        session.add(filter_def)
        await session.commit()
        await session.refresh(filter_def)
        return filter_def


async def test_list_filter_definitions_returns_empty_when_none(client, session_factory):
    category = await _create_category(session_factory)
    resp = await client.get(f"/api/categories/{category.id}/filters")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_filter_definitions_returns_all_for_category(
    client, session_factory
):
    category = await _create_category(session_factory)

    await _create_filter(
        session_factory, category_id=category.id, slug="ram", display_order=0
    )
    await _create_filter(
        session_factory,
        category_id=category.id,
        slug="screen_size",
        filter_type="number",
        options=None,
        display_order=1,
    )

    resp = await client.get(f"/api/categories/{category.id}/filters")
    assert resp.status_code == 200
    slugs = [f["slug"] for f in resp.json()]
    assert slugs == ["ram", "screen_size"]


async def test_list_filter_definitions_unknown_category_returns_404(client):
    resp = await client.get("/api/categories/9999/filters")
    assert resp.status_code == 404


async def test_create_filter_definition_requires_moderator_role(
    client, session_factory
):
    category = await _create_category(session_factory)
    token = await _register(client, email="user@test.com", username="user")

    resp = await client.post(
        f"/api/categories/{category.id}/filters",
        headers=_auth_header(token),
        json=_filter_payload(),
    )
    assert resp.status_code == 403


async def test_create_filter_definition(client, session_factory):
    category = await _create_category(session_factory)
    await _create_moderator(session_factory)
    token = await _login(client, email="moderator@test.com")

    resp = await client.post(
        f"/api/categories/{category.id}/filters",
        headers=_auth_header(token),
        json=_filter_payload(),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["slug"] == "ram"
    assert data["filter_type"] == "select"
    assert data["category_id"] == category.id


async def test_create_filter_definition_duplicate_slug_returns_409(
    client, session_factory
):
    category = await _create_category(session_factory)
    await _create_moderator(session_factory)
    token = await _login(client, email="moderator@test.com")

    await _create_filter(session_factory, category_id=category.id)

    resp = await client.post(
        f"/api/categories/{category.id}/filters",
        headers=_auth_header(token),
        json=_filter_payload(),
    )
    assert resp.status_code == 409


async def test_create_select_filter_without_options_values_returns_422(
    client, session_factory
):
    category = await _create_category(session_factory)
    await _create_moderator(session_factory)
    token = await _login(client, email="moderator@test.com")

    resp = await client.post(
        f"/api/categories/{category.id}/filters",
        headers=_auth_header(token),
        json=_filter_payload(filter_type="select", options=None),
    )
    assert resp.status_code == 422


async def test_create_filter_definition_invalid_slug_returns_422(
    client, session_factory
):
    category = await _create_category(session_factory)
    await _create_moderator(session_factory)
    token = await _login(client, email="moderator@test.com")

    resp = await client.post(
        f"/api/categories/{category.id}/filters",
        headers=_auth_header(token),
        json=_filter_payload(slug="Invalid Slug!"),
    )
    assert resp.status_code == 422


async def test_update_filter_definition(client, session_factory):
    category = await _create_category(session_factory)
    await _create_moderator(session_factory)
    token = await _login(client, email="moderator@test.com")
    definition = await _create_filter(session_factory, category_id=category.id)

    resp = await client.patch(
        f"/api/categories/{category.id}/filters/{definition.id}",
        headers=_auth_header(token),
        json={"label": "RAM Memory", "is_required": True},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["label"] == "RAM Memory"
    assert data["is_required"] is True
    assert data["slug"] == "ram"  # unchanged


async def test_update_filter_definition_to_select_without_options_returns_400(
    client, session_factory
):
    category = await _create_category(session_factory)
    await _create_moderator(session_factory)
    token = await _login(client, email="moderator@test.com")
    definition = await _create_filter(
        session_factory,
        category_id=category.id,
        filter_type="text",
        options=None,
    )

    resp = await client.patch(
        f"/api/categories/{category.id}/filters/{definition.id}",
        headers=_auth_header(token),
        json={"filter_type": "select"},  # no options provided — service must catch this
    )
    assert resp.status_code == 400


async def test_delete_filter_definition(client, session_factory):
    category = await _create_category(session_factory)
    await _create_moderator(session_factory)
    token = await _login(client, email="moderator@test.com")
    definition = await _create_filter(session_factory, category_id=category.id)

    resp = await client.delete(
        f"/api/categories/{category.id}/filters/{definition.id}",
        headers=_auth_header(token),
    )
    assert resp.status_code == 204

    resp = await client.get(f"/api/categories/{category.id}/filters")
    assert resp.json() == []


async def test_delete_filter_definition_not_found_returns_404(client, session_factory):
    category = await _create_category(session_factory)
    await _create_moderator(session_factory)
    token = await _login(client, email="moderator@test.com")

    resp = await client.delete(
        f"/api/categories/{category.id}/filters/9999",
        headers=_auth_header(token),
    )
    assert resp.status_code == 404
