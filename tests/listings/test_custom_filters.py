"""
Tests for custom_filters validation on listing create/update.
Note: filtering listings by custom_filters via @> operator requires PostgreSQL
and is not tested here (SQLite does not support JSONB containment queries).
"""

import itertools
import uuid

from src.domains.categories.models import Category
from tests.helpers.auth import auth_header, login_user, register_user
from tests.helpers.listings import create_category

_cat_id = itertools.count(1)
from src.domains.users.enums import UserRole
from src.domains.users.models import User


def _auth_header(token: str) -> dict:
    return auth_header(token)


async def _register(client, *, email: str, username: str) -> str:
    data = await register_user(
        client, email=email, username=username, device_id="device"
    )
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
    return await create_category(
        session_factory, name=name, depth=0, category_id=next(_cat_id)
    )


async def _create_filter_definition(
    client, *, token: str, category_id: int, payload: dict
) -> dict:
    resp = await client.post(
        f"/api/categories/{category_id}/filters",
        headers=_auth_header(token),
        json=payload,
    )
    assert resp.status_code == 201
    return resp.json()


def _listing_payload(*, category_id: int, custom_filters: dict | None = None) -> dict:
    payload = {
        "title": "Gaming laptop 2026",
        "description": "Powerful gaming laptop with RTX graphics card, clean condition, and full accessories included.",
        "price": 2200,
        "is_free": False,
        "is_tradable": False,
        "currency": "usd",
        "category_id": category_id,
    }
    if custom_filters is not None:
        payload["custom_filters"] = custom_filters
    return payload


async def test_create_listing_with_valid_custom_filters(client, session_factory):
    category = await _create_category(session_factory)
    await _create_moderator(session_factory)
    mod_token = await _login(client, email="moderator@test.com")
    await _create_filter_definition(
        client,
        token=mod_token,
        category_id=category.id,
        payload={
            "slug": "ram",
            "label": "RAM",
            "filter_type": "select",
            "options": {"values": ["8 GB", "16 GB", "32 GB"]},
            "is_required": False,
            "display_order": 0,
        },
    )

    user_token = await _register(client, email="user@test.com", username="user")
    resp = await client.post(
        "/api/listings",
        headers=_auth_header(user_token),
        json=_listing_payload(category_id=category.id, custom_filters={"ram": "16 GB"}),
    )
    assert resp.status_code == 200
    assert resp.json()["custom_filters"] == {"ram": "16 GB"}


async def test_create_listing_with_missing_required_filter_returns_400(
    client, session_factory
):
    category = await _create_category(session_factory)
    await _create_moderator(session_factory)
    mod_token = await _login(client, email="moderator@test.com")
    await _create_filter_definition(
        client,
        token=mod_token,
        category_id=category.id,
        payload={
            "slug": "ram",
            "label": "RAM",
            "filter_type": "select",
            "options": {"values": ["8 GB", "16 GB"]},
            "is_required": True,
            "display_order": 0,
        },
    )

    user_token = await _register(client, email="user@test.com", username="user")
    resp = await client.post(
        "/api/listings",
        headers=_auth_header(user_token),
        json=_listing_payload(category_id=category.id, custom_filters={}),
    )
    assert resp.status_code == 400


async def test_create_listing_with_unknown_filter_key_returns_400(
    client, session_factory
):
    category = await _create_category(session_factory)
    await _create_moderator(session_factory)
    mod_token = await _login(client, email="moderator@test.com")
    await _create_filter_definition(
        client,
        token=mod_token,
        category_id=category.id,
        payload={
            "slug": "ram",
            "label": "RAM",
            "filter_type": "select",
            "options": {"values": ["8 GB", "16 GB"]},
            "is_required": False,
            "display_order": 0,
        },
    )

    user_token = await _register(client, email="user@test.com", username="user")
    resp = await client.post(
        "/api/listings",
        headers=_auth_header(user_token),
        json=_listing_payload(
            category_id=category.id,
            custom_filters={"ram": "8 GB", "unknown_key": "value"},
        ),
    )
    assert resp.status_code == 400


async def test_create_listing_with_invalid_select_option_returns_400(
    client, session_factory
):
    category = await _create_category(session_factory)
    await _create_moderator(session_factory)
    mod_token = await _login(client, email="moderator@test.com")
    await _create_filter_definition(
        client,
        token=mod_token,
        category_id=category.id,
        payload={
            "slug": "color",
            "label": "Color",
            "filter_type": "select",
            "options": {"values": ["red", "blue", "green"]},
            "is_required": False,
            "display_order": 0,
        },
    )

    user_token = await _register(client, email="user@test.com", username="user")
    resp = await client.post(
        "/api/listings",
        headers=_auth_header(user_token),
        json=_listing_payload(
            category_id=category.id,
            custom_filters={"color": "purple"},
        ),
    )
    assert resp.status_code == 400


async def test_create_listing_with_wrong_type_for_number_filter_returns_400(
    client, session_factory
):
    category = await _create_category(session_factory)
    await _create_moderator(session_factory)
    mod_token = await _login(client, email="moderator@test.com")
    await _create_filter_definition(
        client,
        token=mod_token,
        category_id=category.id,
        payload={
            "slug": "screen_size",
            "label": "Screen size",
            "filter_type": "number",
            "options": None,
            "is_required": False,
            "display_order": 0,
        },
    )

    user_token = await _register(client, email="user@test.com", username="user")
    resp = await client.post(
        "/api/listings",
        headers=_auth_header(user_token),
        json=_listing_payload(
            category_id=category.id,
            custom_filters={"screen_size": "fifteen"},
        ),
    )
    assert resp.status_code == 400


async def test_create_listing_without_filters_when_category_has_no_definitions(
    client, session_factory
):
    category = await _create_category(session_factory)
    user_token = await _register(client, email="user@test.com", username="user")

    resp = await client.post(
        "/api/listings",
        headers=_auth_header(user_token),
        json=_listing_payload(category_id=category.id),
    )
    assert resp.status_code == 200
