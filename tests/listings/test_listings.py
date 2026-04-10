import itertools
import uuid

from sqlalchemy import inspect

from src.core.database.repositories import Repositories
from src.domains.categories.models import Category
from src.domains.listings.enums import CurrencyEnum, ListingStatus

_cat_id = itertools.count(1)


# ── helpers ──────────────────────────────────────────────────────────────────


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _register(
    client, *, email: str, username: str, device_id: str = "device"
) -> str:
    resp = await client.post(
        "/api/auth/register",
        json={
            "email": email,
            "username": username,
            "password": "strong-password",
            "device_id": device_id,
        },
    )
    assert resp.status_code == 201
    return resp.json()["access_token"]


async def _create_category(session_factory, *, name: str) -> Category:
    async with session_factory() as session:
        category = Category(id=next(_cat_id), name=name, depth=0)
        session.add(category)
        await session.commit()
        await session.refresh(category)
        return category


def _listing_payload(*, category_id: int) -> dict:
    return {
        "title": "Gaming laptop 2026",
        "description": "Powerful gaming laptop with RTX graphics card, clean condition, and full accessories included.",
        "price": 2200,
        "is_free": False,
        "is_tradable": False,
        "currency": "usd",
        "category_id": category_id,
    }


async def _create_listing(client, *, token: str, category_id: int) -> dict:
    resp = await client.post(
        "/api/listings",
        headers=_auth_header(token),
        json=_listing_payload(category_id=category_id),
    )
    assert resp.status_code == 200
    return resp.json()


# ── POST /api/listings ────────────────────────────────────────────────────────


async def test_create_listing_sets_inactive_status(client, session_factory):
    category = await _create_category(session_factory, name="Electronics")
    token = await _register(client, email="u1@example.com", username="u12")

    body = await _create_listing(client, token=token, category_id=category.id)

    assert body["status"] == "inactive"
    assert body["category"]["id"] == category.id


async def test_create_listing_requires_auth(client, session_factory):
    category = await _create_category(session_factory, name="Electronics")

    resp = await client.post(
        "/api/listings", json=_listing_payload(category_id=category.id)
    )

    assert resp.status_code == 401


async def test_create_listing_with_unknown_category_returns_404(client):
    token = await _register(client, email="u2@example.com", username="u22")

    resp = await client.post(
        "/api/listings",
        headers=_auth_header(token),
        json=_listing_payload(category_id=999999),
    )

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Category not found"


# ── GET /api/listings ─────────────────────────────────────────────────────────


async def test_list_listings_excludes_inactive(client, session_factory):
    category = await _create_category(session_factory, name="Electronics")
    token = await _register(client, email="u3@example.com", username="u32")
    listing = await _create_listing(client, token=token, category_id=category.id)

    resp = await client.get("/api/listings")

    assert resp.status_code == 200
    assert not any(l["id"] == listing["id"] for l in resp.json()["listings"])


async def test_list_listings_includes_active(client, session_factory):
    category = await _create_category(session_factory, name="Electronics")
    token = await _register(client, email="u4@example.com", username="u42")
    listing = await _create_listing(client, token=token, category_id=category.id)

    await client.put(
        f"/api/listings/{listing['id']}/status",
        headers=_auth_header(token),
        json={"status": "active"},
    )

    resp = await client.get("/api/listings")

    assert resp.status_code == 200
    assert any(l["id"] == listing["id"] for l in resp.json()["listings"])


# ── GET /api/listings/{id} ────────────────────────────────────────────────────


async def test_get_listing_by_id(client, session_factory):
    category = await _create_category(session_factory, name="Electronics")
    token = await _register(client, email="u5@example.com", username="u52")
    listing = await _create_listing(client, token=token, category_id=category.id)

    resp = await client.get(f"/api/listings/{listing['id']}")

    assert resp.status_code == 200
    assert resp.json()["id"] == listing["id"]


async def test_get_listing_not_found_returns_404(client):
    resp = await client.get(f"/api/listings/{uuid.uuid4()}")

    assert resp.status_code == 404


# ── PUT /api/listings/{id} ────────────────────────────────────────────────────


async def test_update_listing_changes_category(client, session_factory):
    cat_a = await _create_category(session_factory, name="Phones")
    cat_b = await _create_category(session_factory, name="Laptops")
    token = await _register(client, email="u6@example.com", username="u62")
    listing = await _create_listing(client, token=token, category_id=cat_a.id)

    resp = await client.put(
        f"/api/listings/{listing['id']}",
        headers=_auth_header(token),
        json=_listing_payload(category_id=cat_b.id),
    )

    assert resp.status_code == 200
    assert resp.json()["category"]["id"] == cat_b.id


async def test_update_listing_with_unknown_category_returns_404(
    client, session_factory
):
    category = await _create_category(session_factory, name="Monitors")
    token = await _register(client, email="u7@example.com", username="u72")
    listing = await _create_listing(client, token=token, category_id=category.id)

    resp = await client.put(
        f"/api/listings/{listing['id']}",
        headers=_auth_header(token),
        json=_listing_payload(category_id=999999),
    )

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Category not found"


async def test_update_listing_by_non_owner_returns_403(client, session_factory):
    category = await _create_category(session_factory, name="Electronics")
    owner_token = await _register(client, email="owner@example.com", username="owner")
    other_token = await _register(
        client, email="other@example.com", username="other", device_id="device-2"
    )
    listing = await _create_listing(client, token=owner_token, category_id=category.id)

    resp = await client.put(
        f"/api/listings/{listing['id']}",
        headers=_auth_header(other_token),
        json=_listing_payload(category_id=category.id),
    )

    assert resp.status_code == 403


# ── PUT /api/listings/{id}/status ─────────────────────────────────────────────


async def test_update_listing_status(client, session_factory):
    category = await _create_category(session_factory, name="Electronics")
    token = await _register(client, email="u8@example.com", username="u82")
    listing = await _create_listing(client, token=token, category_id=category.id)

    resp = await client.put(
        f"/api/listings/{listing['id']}/status",
        headers=_auth_header(token),
        json={"status": "active"},
    )

    assert resp.status_code == 200
    assert resp.json()["status"] == "active"


async def test_update_listing_status_by_non_owner_returns_403(client, session_factory):
    category = await _create_category(session_factory, name="Electronics")
    owner_token = await _register(client, email="owner2@example.com", username="owner2")
    other_token = await _register(
        client, email="other2@example.com", username="other2", device_id="device-2"
    )
    listing = await _create_listing(client, token=owner_token, category_id=category.id)

    resp = await client.put(
        f"/api/listings/{listing['id']}/status",
        headers=_auth_header(other_token),
        json={"status": "active"},
    )

    assert resp.status_code == 403


# ── GET /api/users/me/listings ────────────────────────────────────────────────


async def test_get_my_listings_returns_all_statuses(client, session_factory):
    category = await _create_category(session_factory, name="Electronics")
    token = await _register(client, email="u9@example.com", username="u91")
    listing = await _create_listing(client, token=token, category_id=category.id)

    resp = await client.get("/api/users/me/listings", headers=_auth_header(token))

    assert resp.status_code == 200
    assert any(l["id"] == listing["id"] for l in resp.json()["listings"])


async def test_get_my_listings_filter_by_status(client, session_factory):
    category = await _create_category(session_factory, name="Electronics")
    token = await _register(client, email="u10@example.com", username="u10")
    listing = await _create_listing(client, token=token, category_id=category.id)
    listing_id = listing["id"]
    headers = _auth_header(token)

    active_resp = await client.get(
        "/api/users/me/listings?status=active", headers=headers
    )
    assert active_resp.status_code == 200
    assert not any(l["id"] == listing_id for l in active_resp.json()["listings"])

    inactive_resp = await client.get(
        "/api/users/me/listings?status=inactive", headers=headers
    )
    assert inactive_resp.status_code == 200
    assert any(l["id"] == listing_id for l in inactive_resp.json()["listings"])


async def test_get_my_listings_requires_auth(client):
    resp = await client.get("/api/users/me/listings")

    assert resp.status_code == 401


# ── GET /api/users/{username}/listings ────────────────────────────────────────


async def test_get_user_listings_returns_only_active(client, session_factory):
    category = await _create_category(session_factory, name="Electronics")
    token = await _register(client, email="u11@example.com", username="u11")
    listing = await _create_listing(client, token=token, category_id=category.id)

    await client.put(
        f"/api/listings/{listing['id']}/status",
        headers=_auth_header(token),
        json={"status": "active"},
    )

    resp = await client.get("/api/users/u11/listings")

    assert resp.status_code == 200
    assert any(l["id"] == listing["id"] for l in resp.json()["listings"])


async def test_get_user_listings_hides_inactive(client, session_factory):
    category = await _create_category(session_factory, name="Electronics")
    token = await _register(client, email="u12@example.com", username="u12")
    listing = await _create_listing(client, token=token, category_id=category.id)

    resp = await client.get("/api/users/u12/listings")

    assert resp.status_code == 200
    assert not any(l["id"] == listing["id"] for l in resp.json()["listings"])


async def test_get_user_listings_unknown_user_returns_404(client):
    resp = await client.get("/api/users/nonexistent-xyz/listings")

    assert resp.status_code == 404


async def test_listings_repository_separates_lean_and_response_reads(session_factory):
    async with session_factory() as session:
        repos = Repositories.from_session(session)
        category = Category(id=next(_cat_id), name="Repo Listings", depth=0)
        session.add(category)

        user = await repos.users.create(
            email="repo-listings@example.com",
            username="repo-listings",
            password_hash="hash",
        )
        listing = await repos.listings.create(
            user_id=user.id,
            category_id=category.id,
            title="Gaming laptop repository",
            description="Repository-level listing description with enough length for validation.",
            price=1234,
            is_free=False,
            is_tradable=False,
            currency=CurrencyEnum.USD,
            status=ListingStatus.ACTIVE,
            custom_filters=None,
        )
        image = await repos.images.create(
            s3_key=f"listings/{listing.id}/repo-image.png",
            content_type="image/png",
            size_bytes=123,
        )
        await repos.listing_images.create(
            listing_id=listing.id,
            image_id=image.id,
            sort_order=0,
        )
        await session.commit()
        listing_id = listing.id

    async with session_factory() as session:
        repos = Repositories.from_session(session)
        lean_listing = await repos.listings.get_by_id(listing_id)
        assert lean_listing is not None
        assert "category" in inspect(lean_listing).unloaded
        assert "images" in inspect(lean_listing).unloaded

    async with session_factory() as session:
        repos = Repositories.from_session(session)
        response_listing = await repos.listings.get_for_response_by_id(listing_id)
        assert response_listing is not None
        assert "category" not in inspect(response_listing).unloaded
        assert "images" not in inspect(response_listing).unloaded
        assert response_listing.images
        assert "image" not in inspect(response_listing.images[0]).unloaded
