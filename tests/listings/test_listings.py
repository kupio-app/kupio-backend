import itertools
import uuid

from sqlalchemy import inspect, select, update, func

from src.core.database.repositories import Repositories
from src.domains.categories.models import Category
from src.domains.chat.models import Conversation
from src.domains.listings.models import ListingView
from src.domains.listings.enums import CurrencyEnum, ListingStatus
from src.domains.promotions.enums import PromotionType
from src.domains.promotions.models import PromotionPacket
from src.domains.users.models import User

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


async def _activate_listing(client, *, token: str, listing_id: str) -> dict:
    resp = await client.put(
        f"/api/listings/{listing_id}/status",
        headers=_auth_header(token),
        json={"status": "active"},
    )
    assert resp.status_code == 200
    return resp.json()


async def _create_packet(
    session_factory,
    *,
    name: str,
    promotion_type: PromotionType = PromotionType.TOP,
    duration_days: int = 7,
    price: int = 1000,
) -> PromotionPacket:
    async with session_factory() as session:
        packet = PromotionPacket(
            name=name,
            description="Stats packet",
            type=promotion_type,
            duration_days=duration_days,
            price=price,
            is_active=True,
        )
        session.add(packet)
        await session.commit()
        await session.refresh(packet)
        return packet


async def _add_balance(session_factory, *, username: str, amount: int) -> None:
    async with session_factory() as session:
        await session.execute(
            update(User).where(User.username == username).values(balance=amount)
        )
        await session.commit()


async def _purchase_promotion(
    client, *, token: str, listing_id: str, packet_id: int
) -> dict:
    resp = await client.post(
        f"/api/listings/promotions/{listing_id}",
        headers=_auth_header(token),
        json={"packet_id": packet_id},
    )
    assert resp.status_code == 201
    return resp.json()


async def _count_views(session_factory, *, listing_id: str) -> int:
    async with session_factory() as session:
        stmt = select(func.count(ListingView.id)).where(
            ListingView.listing_id == uuid.UUID(listing_id)
        )
        return int((await session.scalar(stmt)) or 0)


async def _get_views(session_factory, *, listing_id: str) -> list[ListingView]:
    async with session_factory() as session:
        stmt = select(ListingView).where(
            ListingView.listing_id == uuid.UUID(listing_id)
        )
        return list((await session.scalars(stmt)).all())


async def _create_conversation(
    session_factory,
    *,
    listing_id: str,
    buyer_username: str,
    seller_username: str,
) -> Conversation:
    async with session_factory() as session:
        buyer = await session.scalar(
            select(User).where(User.username == buyer_username)
        )
        seller = await session.scalar(
            select(User).where(User.username == seller_username)
        )
        conversation = Conversation(
            listing_id=uuid.UUID(listing_id),
            buyer_id=buyer.id,
            seller_id=seller.id,
        )
        session.add(conversation)
        await session.commit()
        await session.refresh(conversation)
        return conversation


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


async def test_get_listing_does_not_count_seen_by_default(client, session_factory):
    category = await _create_category(session_factory, name="Electronics")
    seller_token = await _register(
        client, email="seller-seen1@example.com", username="seller-seen1"
    )
    buyer_token = await _register(
        client, email="buyer-seen1@example.com", username="buyer-seen1"
    )
    listing = await _create_listing(client, token=seller_token, category_id=category.id)
    await _activate_listing(client, token=seller_token, listing_id=listing["id"])

    resp = await client.get(
        f"/api/listings/{listing['id']}",
        headers=_auth_header(buyer_token),
    )

    assert resp.status_code == 200
    assert await _count_views(session_factory, listing_id=listing["id"]) == 0


async def test_get_listing_does_not_count_seen_when_flag_false(client, session_factory):
    category = await _create_category(session_factory, name="Electronics")
    seller_token = await _register(
        client, email="seller-seen2@example.com", username="seller-seen2"
    )
    buyer_token = await _register(
        client, email="buyer-seen2@example.com", username="buyer-seen2"
    )
    listing = await _create_listing(client, token=seller_token, category_id=category.id)
    await _activate_listing(client, token=seller_token, listing_id=listing["id"])

    resp = await client.get(
        f"/api/listings/{listing['id']}?count_seen=false",
        headers=_auth_header(buyer_token),
    )

    assert resp.status_code == 200
    assert await _count_views(session_factory, listing_id=listing["id"]) == 0


async def test_get_listing_counts_seen_when_flag_true(client, session_factory):
    category = await _create_category(session_factory, name="Electronics")
    seller_token = await _register(
        client, email="seller-seen3@example.com", username="seller-seen3"
    )
    buyer_token = await _register(
        client, email="buyer-seen3@example.com", username="buyer-seen3"
    )
    listing = await _create_listing(client, token=seller_token, category_id=category.id)
    await _activate_listing(client, token=seller_token, listing_id=listing["id"])

    resp = await client.get(
        f"/api/listings/{listing['id']}?count_seen=true",
        headers=_auth_header(buyer_token),
    )

    assert resp.status_code == 200
    assert await _count_views(session_factory, listing_id=listing["id"]) == 1


async def test_get_listing_counts_repeated_anonymous_seen(client, session_factory):
    category = await _create_category(session_factory, name="Electronics")
    seller_token = await _register(
        client, email="seller-seen4@example.com", username="seller-seen4"
    )
    listing = await _create_listing(client, token=seller_token, category_id=category.id)
    await _activate_listing(client, token=seller_token, listing_id=listing["id"])

    first_resp = await client.get(f"/api/listings/{listing['id']}?count_seen=true")
    second_resp = await client.get(f"/api/listings/{listing['id']}?count_seen=true")

    assert first_resp.status_code == 200
    assert second_resp.status_code == 200
    assert await _count_views(session_factory, listing_id=listing["id"]) == 2


async def test_get_listing_does_not_count_owner_seen(client, session_factory):
    category = await _create_category(session_factory, name="Electronics")
    seller_token = await _register(
        client, email="seller-seen5@example.com", username="seller-seen5"
    )
    listing = await _create_listing(client, token=seller_token, category_id=category.id)
    await _activate_listing(client, token=seller_token, listing_id=listing["id"])

    resp = await client.get(
        f"/api/listings/{listing['id']}?count_seen=true",
        headers=_auth_header(seller_token),
    )

    assert resp.status_code == 200
    assert await _count_views(session_factory, listing_id=listing["id"]) == 0


async def test_get_listing_with_invalid_token_stays_public_and_counts_anonymously(
    client, session_factory
):
    category = await _create_category(session_factory, name="Electronics")
    seller_token = await _register(
        client, email="seller-seen6@example.com", username="seller-seen6"
    )
    listing = await _create_listing(client, token=seller_token, category_id=category.id)
    await _activate_listing(client, token=seller_token, listing_id=listing["id"])

    resp = await client.get(
        f"/api/listings/{listing['id']}?count_seen=true",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert resp.status_code == 200
    views = await _get_views(session_factory, listing_id=listing["id"])
    assert len(views) == 1
    assert views[0].viewer_user_id is None


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


async def test_get_my_stats_returns_dashboard_totals(client, session_factory):
    category = await _create_category(session_factory, name="Electronics")
    seller_token = await _register(
        client, email="stats-seller@example.com", username="statsseller"
    )
    buyer_token = await _register(
        client, email="stats-buyer@example.com", username="statsbuyer"
    )
    other_token = await _register(
        client, email="stats-other@example.com", username="statsother"
    )

    promoted_listing = await _create_listing(
        client, token=seller_token, category_id=category.id
    )
    active_listing = await _create_listing(
        client, token=seller_token, category_id=category.id
    )
    inactive_listing = await _create_listing(
        client, token=seller_token, category_id=category.id
    )

    await _activate_listing(
        client, token=seller_token, listing_id=promoted_listing["id"]
    )
    await _activate_listing(client, token=seller_token, listing_id=active_listing["id"])

    await client.get(
        f"/api/listings/{promoted_listing['id']}?count_seen=true",
        headers=_auth_header(buyer_token),
    )
    await client.get(
        f"/api/listings/{promoted_listing['id']}?count_seen=true",
    )

    favourite_resp = await client.post(
        f"/api/listings/favourites/{promoted_listing['id']}",
        headers=_auth_header(buyer_token),
    )
    assert favourite_resp.status_code == 201

    conversation = await _create_conversation(
        session_factory,
        listing_id=promoted_listing["id"],
        buyer_username="statsbuyer",
        seller_username="statsseller",
    )
    assert conversation.id is not None

    unrelated_listing = await _create_listing(
        client, token=other_token, category_id=category.id
    )
    await _activate_listing(
        client, token=other_token, listing_id=unrelated_listing["id"]
    )
    unrelated_favourite = await client.post(
        f"/api/listings/favourites/{unrelated_listing['id']}",
        headers=_auth_header(seller_token),
    )
    assert unrelated_favourite.status_code == 201

    await _add_balance(session_factory, username="statsseller", amount=5000)
    packet = await _create_packet(session_factory, name="Stats Top Packet")
    await _purchase_promotion(
        client,
        token=seller_token,
        listing_id=promoted_listing["id"],
        packet_id=packet.id,
    )

    resp = await client.get("/api/users/me/stats", headers=_auth_header(seller_token))

    assert resp.status_code == 200
    assert resp.json() == {
        "active_count": 2,
        "inactive_count": 1,
        "promoted_count": 1,
        "chats_count": 1,
        "favourites_count": 1,
    }


async def test_get_my_stats_requires_auth(client):
    resp = await client.get("/api/users/me/stats")

    assert resp.status_code == 401


async def test_get_my_listings_include_owner_stats(client, session_factory):
    category = await _create_category(session_factory, name="Electronics")
    seller_token = await _register(
        client, email="owner-stats@example.com", username="ownerstats"
    )
    buyer_token = await _register(
        client, email="viewer-stats@example.com", username="viewerstats"
    )

    promoted_listing = await _create_listing(
        client, token=seller_token, category_id=category.id
    )
    plain_listing = await _create_listing(
        client, token=seller_token, category_id=category.id
    )
    await _activate_listing(
        client, token=seller_token, listing_id=promoted_listing["id"]
    )
    await _activate_listing(client, token=seller_token, listing_id=plain_listing["id"])

    await client.get(
        f"/api/listings/{promoted_listing['id']}?count_seen=true",
        headers=_auth_header(buyer_token),
    )
    await client.get(
        f"/api/listings/{promoted_listing['id']}?count_seen=true",
    )

    favourite_resp = await client.post(
        f"/api/listings/favourites/{promoted_listing['id']}",
        headers=_auth_header(buyer_token),
    )
    assert favourite_resp.status_code == 201

    conversation = await _create_conversation(
        session_factory,
        listing_id=promoted_listing["id"],
        buyer_username="viewerstats",
        seller_username="ownerstats",
    )
    assert conversation.id is not None

    await _add_balance(session_factory, username="ownerstats", amount=5000)
    packet = await _create_packet(session_factory, name="Owner Stats Packet")
    await _purchase_promotion(
        client,
        token=seller_token,
        listing_id=promoted_listing["id"],
        packet_id=packet.id,
    )

    resp = await client.get(
        "/api/users/me/listings?status=active",
        headers=_auth_header(seller_token),
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["next_cursor"] is None
    returned = {listing["id"]: listing for listing in body["listings"]}
    assert set(returned) == {promoted_listing["id"], plain_listing["id"]}

    promoted = returned[promoted_listing["id"]]
    assert promoted["seen_count"] == 2
    assert promoted["favourites_count"] == 1
    assert promoted["chats_count"] == 1
    assert promoted["is_promoted"] is True
    assert promoted["promotion_expires_at"] is not None

    plain = returned[plain_listing["id"]]
    assert plain["seen_count"] == 0
    assert plain["favourites_count"] == 0
    assert plain["chats_count"] == 0
    assert plain["is_promoted"] is False
    assert plain["promotion_expires_at"] is None


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
