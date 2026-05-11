import datetime
import itertools
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.exc import IntegrityError

from src.domains.categories.models import Category
from src.domains.favourites.exceptions import ListingAlreadyFavouritedError
from src.domains.favourites.models import ListingFavourite
from src.domains.favourites.service import FavouritesService
from tests.helpers.auth import auth_header, register_user

_cat_id = itertools.count(1)


def _auth_header(token: str) -> dict:
    return auth_header(token)


async def _register(
    client, *, email: str, username: str, device_id: str = "device"
) -> str:
    data = await register_user(
        client, email=email, username=username, device_id=device_id
    )
    return data["access_token"]


async def _get_current_user_id(client, *, token: str) -> uuid.UUID:
    resp = await client.get("/api/users/me", headers=_auth_header(token))
    assert resp.status_code == 200
    return uuid.UUID(resp.json()["id"])


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


async def _set_listing_status(
    client, *, token: str, listing_id: str, status: str
) -> None:
    resp = await client.put(
        f"/api/listings/{listing_id}/status",
        headers=_auth_header(token),
        json={"status": status},
    )
    assert resp.status_code == 200


async def _insert_favourite(
    session_factory,
    *,
    user_id: uuid.UUID,
    listing_id: str,
    created_at: datetime.datetime,
) -> None:
    async with session_factory() as session:
        session.add(
            ListingFavourite(
                user_id=user_id,
                listing_id=uuid.UUID(listing_id),
                created_at=created_at,
            )
        )
        await session.commit()


async def test_add_favourite_returns_201(client, session_factory):
    category = await _create_category(session_factory, name="Electronics")
    owner_token = await _register(client, email="owner@example.com", username="owner")
    buyer_token = await _register(
        client, email="buyer@example.com", username="buyer", device_id="device-2"
    )
    listing = await _create_listing(client, token=owner_token, category_id=category.id)

    resp = await client.post(
        f"/api/listings/favourites/{listing['id']}",
        headers=_auth_header(buyer_token),
    )

    assert resp.status_code == 201


async def test_add_favourite_unknown_listing_returns_404(client):
    token = await _register(client, email="u1@example.com", username="usr1")

    resp = await client.post(
        f"/api/listings/favourites/{uuid.uuid4()}",
        headers=_auth_header(token),
    )

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Listing not found"


async def test_add_favourite_own_listing_returns_403(client, session_factory):
    category = await _create_category(session_factory, name="Electronics")
    token = await _register(client, email="u2@example.com", username="usr2")
    listing = await _create_listing(client, token=token, category_id=category.id)

    resp = await client.post(
        f"/api/listings/favourites/{listing['id']}",
        headers=_auth_header(token),
    )

    assert resp.status_code == 403
    assert resp.json()["detail"] == "You cannot favourite your own listing"


async def test_add_favourite_duplicate_returns_409(client, session_factory):
    category = await _create_category(session_factory, name="Electronics")
    owner_token = await _register(client, email="owner2@example.com", username="owner2")
    buyer_token = await _register(
        client, email="buyer2@example.com", username="buyer2", device_id="device-2"
    )
    listing = await _create_listing(client, token=owner_token, category_id=category.id)
    headers = _auth_header(buyer_token)

    first_resp = await client.post(
        f"/api/listings/favourites/{listing['id']}", headers=headers
    )
    second_resp = await client.post(
        f"/api/listings/favourites/{listing['id']}",
        headers=headers,
    )

    assert first_resp.status_code == 201
    assert second_resp.status_code == 409
    assert second_resp.json()["detail"] == "Listing is already in favourites"


class _DummyUoW:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


async def test_add_favourite_translates_integrity_error_to_conflict():
    current_user = SimpleNamespace(id=uuid.uuid4())
    listing_id = uuid.uuid4()
    listing = SimpleNamespace(id=listing_id, user_id=uuid.uuid4())
    listings_repo = SimpleNamespace(get_by_id=AsyncMock(return_value=listing))
    get_by_user_and_listing = AsyncMock(side_effect=[None, object()])
    favourites_repo = SimpleNamespace(
        create=AsyncMock(
            side_effect=IntegrityError(
                "INSERT INTO listing_favourites ...",
                params=None,
                orig=Exception("duplicate key value violates unique constraint"),
            )
        ),
        get_by_user_and_listing=get_by_user_and_listing,
    )
    repos = SimpleNamespace(listings=listings_repo, favourites=favourites_repo)
    service = FavouritesService(repos=repos, uow=_DummyUoW())

    with pytest.raises(ListingAlreadyFavouritedError):
        await service.add_favourite(current_user, listing)

    favourites_repo.create.assert_awaited_once_with(
        user_id=current_user.id,
        listing_id=listing_id,
    )
    assert favourites_repo.get_by_user_and_listing.await_count == 2


async def test_get_favourites_requires_auth(client):
    resp = await client.get("/api/listings/favourites")

    assert resp.status_code == 401


async def test_get_favourites_returns_only_current_user_favourites(
    client, session_factory
):
    category = await _create_category(session_factory, name="Electronics")
    owner_token = await _register(client, email="owner3@example.com", username="owner3")
    user_one_token = await _register(
        client, email="user1@example.com", username="user1", device_id="device-2"
    )
    user_two_token = await _register(
        client, email="user2@example.com", username="user2", device_id="device-3"
    )
    listing_one = await _create_listing(
        client, token=owner_token, category_id=category.id
    )
    listing_two = await _create_listing(
        client, token=owner_token, category_id=category.id
    )

    await client.post(
        f"/api/listings/favourites/{listing_one['id']}",
        headers=_auth_header(user_one_token),
    )
    await client.post(
        f"/api/listings/favourites/{listing_two['id']}",
        headers=_auth_header(user_two_token),
    )

    resp = await client.get(
        "/api/listings/favourites",
        headers=_auth_header(user_one_token),
    )

    assert resp.status_code == 200
    ids = [listing["id"] for listing in resp.json()["listings"]]
    assert ids == [listing_one["id"]]


async def test_get_favourites_includes_non_active_statuses(client, session_factory):
    category = await _create_category(session_factory, name="Electronics")
    owner_token = await _register(client, email="owner4@example.com", username="owner4")
    buyer_token = await _register(
        client, email="buyer4@example.com", username="buyer4", device_id="device-2"
    )
    inactive_listing = await _create_listing(
        client, token=owner_token, category_id=category.id
    )
    sold_listing = await _create_listing(
        client, token=owner_token, category_id=category.id
    )
    await _set_listing_status(
        client,
        token=owner_token,
        listing_id=sold_listing["id"],
        status="sold",
    )

    await client.post(
        f"/api/listings/favourites/{inactive_listing['id']}",
        headers=_auth_header(buyer_token),
    )
    await client.post(
        f"/api/listings/favourites/{sold_listing['id']}",
        headers=_auth_header(buyer_token),
    )

    resp = await client.get(
        "/api/listings/favourites",
        headers=_auth_header(buyer_token),
    )

    assert resp.status_code == 200
    returned = {listing["id"]: listing["status"] for listing in resp.json()["listings"]}
    assert returned[inactive_listing["id"]] == "inactive"
    assert returned[sold_listing["id"]] == "sold"


async def test_get_favourites_is_ordered_by_recently_favourited_and_paginates(
    client,
    session_factory,
):
    category = await _create_category(session_factory, name="Electronics")
    owner_token = await _register(client, email="owner5@example.com", username="owner5")
    buyer_token = await _register(
        client, email="buyer5@example.com", username="buyer5", device_id="device-2"
    )
    buyer_id = await _get_current_user_id(client, token=buyer_token)
    listing_one = await _create_listing(
        client, token=owner_token, category_id=category.id
    )
    listing_two = await _create_listing(
        client, token=owner_token, category_id=category.id
    )
    listing_three = await _create_listing(
        client, token=owner_token, category_id=category.id
    )
    base_time = datetime.datetime(2026, 1, 1, 12, 0, 0)
    await _insert_favourite(
        session_factory,
        user_id=buyer_id,
        listing_id=listing_one["id"],
        created_at=base_time,
    )
    await _insert_favourite(
        session_factory,
        user_id=buyer_id,
        listing_id=listing_two["id"],
        created_at=base_time + datetime.timedelta(minutes=1),
    )
    await _insert_favourite(
        session_factory,
        user_id=buyer_id,
        listing_id=listing_three["id"],
        created_at=base_time + datetime.timedelta(minutes=2),
    )
    headers = _auth_header(buyer_token)

    first_page = await client.get("/api/listings/favourites?limit=2", headers=headers)

    assert first_page.status_code == 200
    first_ids = [listing["id"] for listing in first_page.json()["listings"]]
    assert first_ids == [listing_three["id"], listing_two["id"]]
    assert first_page.json()["next_cursor"] is not None

    second_page = await client.get(
        f"/api/listings/favourites?limit=2&cursor={first_page.json()['next_cursor']}",
        headers=headers,
    )

    assert second_page.status_code == 200
    second_ids = [listing["id"] for listing in second_page.json()["listings"]]
    assert second_ids == [listing_one["id"]]
    assert second_page.json()["next_cursor"] is None


async def test_delete_favourite_returns_204(client, session_factory):
    category = await _create_category(session_factory, name="Electronics")
    owner_token = await _register(client, email="owner6@example.com", username="owner6")
    buyer_token = await _register(
        client, email="buyer6@example.com", username="buyer6", device_id="device-2"
    )
    listing = await _create_listing(client, token=owner_token, category_id=category.id)
    headers = _auth_header(buyer_token)
    await client.post(f"/api/listings/favourites/{listing['id']}", headers=headers)

    resp = await client.delete(
        f"/api/listings/favourites/{listing['id']}", headers=headers
    )

    assert resp.status_code == 204

    list_resp = await client.get("/api/listings/favourites", headers=headers)

    assert list_resp.status_code == 200
    assert list_resp.json()["listings"] == []


async def test_delete_missing_favourite_returns_404(client, session_factory):
    category = await _create_category(session_factory, name="Electronics")
    owner_token = await _register(client, email="owner7@example.com", username="owner7")
    buyer_token = await _register(
        client, email="buyer7@example.com", username="buyer7", device_id="device-2"
    )
    listing = await _create_listing(client, token=owner_token, category_id=category.id)

    resp = await client.delete(
        f"/api/listings/favourites/{listing['id']}",
        headers=_auth_header(buyer_token),
    )

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Listing is not in favourites"
