import itertools
import uuid

from sqlalchemy import inspect, select, update, func
from sqlalchemy.dialects import postgresql

from src.core.database.repositories import Repositories
from src.domains.categories.models import Category
from src.domains.chat.models import Conversation
from src.domains.listings.models import Listing, ListingView
from src.domains.listings.enums import CurrencyEnum, ListingStatus
from src.domains.listings.repository import ListingsRepository
from src.domains.promotions.enums import PromotionType
from src.domains.promotions.models import PromotionPacket
from src.domains.users.models import User
from tests.helpers.auth import auth_header, register_user
from tests.helpers.listings import (
    activate_listing,
    create_category,
    create_listing,
    listing_payload,
)

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


async def _create_category(session_factory, *, name: str) -> Category:
    return await create_category(
        session_factory, name=name, depth=0, category_id=next(_cat_id)
    )


def _listing_payload(**kwargs) -> dict:
    return listing_payload(**kwargs)


async def _create_listing(client, *, token: str, category_id: int, **kwargs) -> dict:
    return await create_listing(client, token=token, category_id=category_id, **kwargs)


async def _activate_listing(client, *, token: str, listing_id: str) -> dict:
    return await activate_listing(client, token=token, listing_id=listing_id)


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
    assert not any(item["id"] == listing["id"] for item in resp.json()["listings"])


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
    assert any(item["id"] == listing["id"] for item in resp.json()["listings"])


async def test_list_listings_searches_by_title_substring(client, session_factory):
    category = await _create_category(session_factory, name="Phones")
    token = await _register(client, email="search-title@example.com", username="stitle")
    matching = await _create_listing(
        client,
        token=token,
        category_id=category.id,
        title="Apple iPhone 15 Pro",
    )
    non_matching = await _create_listing(
        client,
        token=token,
        category_id=category.id,
        title="Samsung Galaxy S25 Ultra",
    )
    await _activate_listing(client, token=token, listing_id=matching["id"])
    await _activate_listing(client, token=token, listing_id=non_matching["id"])

    resp = await client.get("/api/listings?q=iPhone")

    assert resp.status_code == 200
    returned_ids = {listing["id"] for listing in resp.json()["listings"]}
    assert matching["id"] in returned_ids
    assert non_matching["id"] not in returned_ids


async def test_list_listings_searches_by_description_substring(client, session_factory):
    category = await _create_category(session_factory, name="Phones")
    token = await _register(client, email="search-desc@example.com", username="sdesc")
    matching = await _create_listing(
        client,
        token=token,
        category_id=category.id,
        title="Flagship phone bundle",
        description="Excellent flagship bundle with Apple iPhone accessories, charger, and protective case included.",
    )
    non_matching = await _create_listing(
        client,
        token=token,
        category_id=category.id,
        title="Office monitor 4K",
        description="Large 4K monitor for office work with adjustable stand, sharp colors, and long warranty period.",
    )
    await _activate_listing(client, token=token, listing_id=matching["id"])
    await _activate_listing(client, token=token, listing_id=non_matching["id"])

    resp = await client.get("/api/listings?q=iPhone")

    assert resp.status_code == 200
    returned_ids = {listing["id"] for listing in resp.json()["listings"]}
    assert matching["id"] in returned_ids
    assert non_matching["id"] not in returned_ids


async def test_list_listings_search_returns_all_matching_results(
    client, session_factory
):
    category = await _create_category(session_factory, name="Phones")
    token = await _register(client, email="search-multi@example.com", username="smulti")
    listings = [
        await _create_listing(
            client,
            token=token,
            category_id=category.id,
            title="Apple iPhone 15 Pro",
        ),
        await _create_listing(
            client,
            token=token,
            category_id=category.id,
            title="Apple iPhone 16 Pro",
        ),
        await _create_listing(
            client,
            token=token,
            category_id=category.id,
            title="Apple iPhone 17 Pro",
        ),
    ]
    for listing in listings:
        await _activate_listing(client, token=token, listing_id=listing["id"])

    resp = await client.get("/api/listings?q=iPhone")

    assert resp.status_code == 200
    returned_ids = {listing["id"] for listing in resp.json()["listings"]}
    assert returned_ids == {listing["id"] for listing in listings}


async def test_list_listings_search_treats_wildcards_as_literal_text(
    client, session_factory
):
    category = await _create_category(session_factory, name="Phones")
    token = await _register(
        client, email="search-wildcards@example.com", username="swildcards"
    )
    percent_listing = await _create_listing(
        client,
        token=token,
        category_id=category.id,
        title="Battery at 100% health",
    )
    underscore_listing = await _create_listing(
        client,
        token=token,
        category_id=category.id,
        title="Model iphone_case bundle",
    )
    wildcard_only = await _create_listing(
        client,
        token=token,
        category_id=category.id,
        title="Regular iPhone case bundle",
    )
    await _activate_listing(client, token=token, listing_id=percent_listing["id"])
    await _activate_listing(client, token=token, listing_id=underscore_listing["id"])
    await _activate_listing(client, token=token, listing_id=wildcard_only["id"])

    percent_resp = await client.get("/api/listings?q=100%")
    underscore_resp = await client.get("/api/listings?q=iphone_")

    assert percent_resp.status_code == 200
    assert underscore_resp.status_code == 200
    percent_ids = {listing["id"] for listing in percent_resp.json()["listings"]}
    underscore_ids = {listing["id"] for listing in underscore_resp.json()["listings"]}
    assert percent_ids == {percent_listing["id"]}
    assert underscore_ids == {underscore_listing["id"]}


async def test_list_listings_search_combines_with_category_filter(
    client, session_factory
):
    phones = await _create_category(session_factory, name="Phones")
    laptops = await _create_category(session_factory, name="Laptops")
    token = await _register(
        client, email="search-category@example.com", username="scategory"
    )
    phone_listing = await _create_listing(
        client,
        token=token,
        category_id=phones.id,
        title="Apple iPhone 16 Pro",
    )
    laptop_listing = await _create_listing(
        client,
        token=token,
        category_id=laptops.id,
        title="iPhone listed in wrong category",
    )
    await _activate_listing(client, token=token, listing_id=phone_listing["id"])
    await _activate_listing(client, token=token, listing_id=laptop_listing["id"])

    resp = await client.get(f"/api/listings?q=iPhone&category_id={phones.id}")

    assert resp.status_code == 200
    returned_ids = {listing["id"] for listing in resp.json()["listings"]}
    assert returned_ids == {phone_listing["id"]}


async def test_list_listings_search_combines_with_custom_filters(
    client, session_factory
):
    conditions = ListingsRepository._search_conditions(
        q="iPhone",
        custom_filters={"ram": "16 GB"},
    )
    stmt = select(Listing).where(*conditions)
    compiled = stmt.compile(
        dialect=postgresql.dialect(),
    )
    sql = str(compiled)
    params = list(compiled.params.values())

    assert "ILIKE" in sql
    assert "@>" in sql
    assert params.count("%iPhone%") == 2
    assert any(param == {"ram": "16 GB"} for param in params)


async def test_list_listings_filters_by_min_price(client, session_factory):
    category = await _create_category(session_factory, name="Phones")
    token = await _register(
        client, email="search-min-price@example.com", username="sminprice"
    )
    cheaper = await _create_listing(
        client,
        token=token,
        category_id=category.id,
        title="Apple iPhone 14 Mini",
        price=150,
    )
    pricier = await _create_listing(
        client,
        token=token,
        category_id=category.id,
        title="Apple iPhone 16 Pro",
        price=950,
    )
    await _activate_listing(client, token=token, listing_id=cheaper["id"])
    await _activate_listing(client, token=token, listing_id=pricier["id"])

    resp = await client.get("/api/listings?q=iPhone&min_price=500")

    assert resp.status_code == 200
    returned_ids = {listing["id"] for listing in resp.json()["listings"]}
    assert returned_ids == {pricier["id"]}


async def test_list_listings_filters_by_max_price(client, session_factory):
    category = await _create_category(session_factory, name="Phones")
    token = await _register(
        client, email="search-max-price@example.com", username="smaxprice"
    )
    free_listing = await _create_listing(
        client,
        token=token,
        category_id=category.id,
        title="Apple iPhone 13 Free",
        price=999,
        is_free=True,
    )
    cheaper = await _create_listing(
        client,
        token=token,
        category_id=category.id,
        title="Apple iPhone 14",
        price=80,
    )
    pricier = await _create_listing(
        client,
        token=token,
        category_id=category.id,
        title="Apple iPhone 16 Pro",
        price=900,
    )
    await _activate_listing(client, token=token, listing_id=free_listing["id"])
    await _activate_listing(client, token=token, listing_id=cheaper["id"])
    await _activate_listing(client, token=token, listing_id=pricier["id"])

    resp = await client.get("/api/listings?q=iPhone&max_price=100")

    assert resp.status_code == 200
    returned_ids = {listing["id"] for listing in resp.json()["listings"]}
    assert returned_ids == {free_listing["id"], cheaper["id"]}


async def test_list_listings_filters_by_price_range(client, session_factory):
    category = await _create_category(session_factory, name="Phones")
    token = await _register(client, email="search-range@example.com", username="srange")
    too_low = await _create_listing(
        client,
        token=token,
        category_id=category.id,
        title="Apple iPhone 13",
        price=90,
    )
    in_range = await _create_listing(
        client,
        token=token,
        category_id=category.id,
        title="Apple iPhone 15 Pro",
        price=350,
    )
    too_high = await _create_listing(
        client,
        token=token,
        category_id=category.id,
        title="Apple iPhone 17 Pro",
        price=1200,
    )
    await _activate_listing(client, token=token, listing_id=too_low["id"])
    await _activate_listing(client, token=token, listing_id=in_range["id"])
    await _activate_listing(client, token=token, listing_id=too_high["id"])

    resp = await client.get("/api/listings?q=iPhone&min_price=100&max_price=500")

    assert resp.status_code == 200
    returned_ids = {listing["id"] for listing in resp.json()["listings"]}
    assert returned_ids == {in_range["id"]}


async def test_list_listings_treats_free_listings_as_zero_price(
    client, session_factory
):
    category = await _create_category(session_factory, name="Phones")
    token = await _register(client, email="search-free@example.com", username="sfree")
    free_listing = await _create_listing(
        client,
        token=token,
        category_id=category.id,
        title="Apple iPhone Free Offer",
        price=999,
        is_free=True,
    )
    await _activate_listing(client, token=token, listing_id=free_listing["id"])

    resp = await client.get("/api/listings?q=iPhone&max_price=0")

    assert resp.status_code == 200
    returned_ids = {listing["id"] for listing in resp.json()["listings"]}
    assert returned_ids == {free_listing["id"]}


async def test_list_listings_excludes_free_listings_when_min_price_is_positive(
    client, session_factory
):
    category = await _create_category(session_factory, name="Phones")
    token = await _register(
        client, email="search-free-min@example.com", username="sfreemin"
    )
    free_listing = await _create_listing(
        client,
        token=token,
        category_id=category.id,
        title="Apple iPhone Giveaway",
        price=500,
        is_free=True,
    )
    await _activate_listing(client, token=token, listing_id=free_listing["id"])

    resp = await client.get("/api/listings?q=iPhone&min_price=1")

    assert resp.status_code == 200
    assert resp.json()["listings"] == []


async def test_list_listings_filters_tradable_by_stored_price(client, session_factory):
    category = await _create_category(session_factory, name="Phones")
    token = await _register(
        client, email="search-tradable@example.com", username="stradable"
    )
    matching = await _create_listing(
        client,
        token=token,
        category_id=category.id,
        title="Apple iPhone 16 Trade",
        price=450,
        is_tradable=True,
    )
    non_matching = await _create_listing(
        client,
        token=token,
        category_id=category.id,
        title="Apple iPhone 15 Trade",
        price=200,
        is_tradable=True,
    )
    await _activate_listing(client, token=token, listing_id=matching["id"])
    await _activate_listing(client, token=token, listing_id=non_matching["id"])

    resp = await client.get("/api/listings?q=iPhone&min_price=300&max_price=500")

    assert resp.status_code == 200
    returned_ids = {listing["id"] for listing in resp.json()["listings"]}
    assert returned_ids == {matching["id"]}


async def test_list_listings_filters_by_is_free(client, session_factory):
    category = await _create_category(session_factory, name="Phones")
    token = await _register(
        client, email="search-is-free@example.com", username="sisfree"
    )
    free_listing = await _create_listing(
        client,
        token=token,
        category_id=category.id,
        title="Apple iPhone 15 Free",
        is_free=True,
        price=700,
    )
    priced_listing = await _create_listing(
        client,
        token=token,
        category_id=category.id,
        title="Apple iPhone 16 Pro",
    )
    await _activate_listing(client, token=token, listing_id=free_listing["id"])
    await _activate_listing(client, token=token, listing_id=priced_listing["id"])

    resp = await client.get("/api/listings?q=iPhone&is_free=true")

    assert resp.status_code == 200
    returned_ids = {listing["id"] for listing in resp.json()["listings"]}
    assert returned_ids == {free_listing["id"]}


async def test_list_listings_filters_by_is_tradable(client, session_factory):
    category = await _create_category(session_factory, name="Phones")
    token = await _register(
        client, email="search-is-tradable@example.com", username="sistradable"
    )
    tradable_listing = await _create_listing(
        client,
        token=token,
        category_id=category.id,
        title="Apple iPhone 15 Swap",
        is_tradable=True,
    )
    non_tradable_listing = await _create_listing(
        client,
        token=token,
        category_id=category.id,
        title="Apple iPhone 16 Pro",
    )
    await _activate_listing(client, token=token, listing_id=tradable_listing["id"])
    await _activate_listing(client, token=token, listing_id=non_tradable_listing["id"])

    resp = await client.get("/api/listings?q=iPhone&is_tradable=true")

    assert resp.status_code == 200
    returned_ids = {listing["id"] for listing in resp.json()["listings"]}
    assert returned_ids == {tradable_listing["id"]}


async def test_list_listings_filters_by_is_free_false(client, session_factory):
    category = await _create_category(session_factory, name="Phones")
    token = await _register(
        client, email="search-not-free@example.com", username="snotfree"
    )
    free_listing = await _create_listing(
        client,
        token=token,
        category_id=category.id,
        title="Apple iPhone 15 Free",
        is_free=True,
        price=400,
    )
    priced_listing = await _create_listing(
        client,
        token=token,
        category_id=category.id,
        title="Apple iPhone 16 Pro",
    )
    await _activate_listing(client, token=token, listing_id=free_listing["id"])
    await _activate_listing(client, token=token, listing_id=priced_listing["id"])

    resp = await client.get("/api/listings?q=iPhone&is_free=false")

    assert resp.status_code == 200
    returned_ids = {listing["id"] for listing in resp.json()["listings"]}
    assert returned_ids == {priced_listing["id"]}


async def test_list_listings_supports_combined_boolean_filters(client, session_factory):
    category = await _create_category(session_factory, name="Phones")
    token = await _register(client, email="search-combo@example.com", username="scombo")
    matching = await _create_listing(
        client,
        token=token,
        category_id=category.id,
        title="Apple iPhone Combo",
        is_free=True,
        is_tradable=True,
        price=500,
    )
    free_only = await _create_listing(
        client,
        token=token,
        category_id=category.id,
        title="Apple iPhone Free",
        is_free=True,
        is_tradable=False,
        price=500,
    )
    tradable_only = await _create_listing(
        client,
        token=token,
        category_id=category.id,
        title="Apple iPhone Trade",
        is_free=False,
        is_tradable=True,
        price=500,
    )
    await _activate_listing(client, token=token, listing_id=matching["id"])
    await _activate_listing(client, token=token, listing_id=free_only["id"])
    await _activate_listing(client, token=token, listing_id=tradable_only["id"])

    resp = await client.get("/api/listings?q=iPhone&is_free=true&is_tradable=true")

    assert resp.status_code == 200
    returned_ids = {listing["id"] for listing in resp.json()["listings"]}
    assert returned_ids == {matching["id"]}


async def test_list_listings_rejects_invalid_price_range(client):
    resp = await client.get("/api/listings?min_price=200&max_price=100")

    assert resp.status_code == 422
    assert resp.json()["detail"] == "min_price must be less than or equal to max_price"


async def test_list_listings_ignores_blank_query(client, session_factory):
    category = await _create_category(session_factory, name="Phones")
    token = await _register(client, email="search-blank@example.com", username="sblank")
    listing = await _create_listing(client, token=token, category_id=category.id)
    await _activate_listing(client, token=token, listing_id=listing["id"])

    resp = await client.get("/api/listings?q=%20%20%20")

    assert resp.status_code == 200
    assert any(item["id"] == listing["id"] for item in resp.json()["listings"])


# ── GET /api/listings/{id} ────────────────────────────────────────────────────


async def test_get_listing_by_id(client, session_factory):
    category = await _create_category(session_factory, name="Electronics")
    token = await _register(client, email="u5@example.com", username="u52")
    listing = await _create_listing(client, token=token, category_id=category.id)

    resp = await client.get(f"/api/listings/{listing['id']}")

    assert resp.status_code == 200
    assert resp.json()["id"] == listing["id"]
    assert resp.json()["seen_count"] == 0


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
    assert resp.json()["seen_count"] == 0
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
    assert resp.json()["seen_count"] == 0
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
    assert resp.json()["seen_count"] == 1
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
    assert second_resp.json()["seen_count"] == 2
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
    assert any(item["id"] == listing["id"] for item in resp.json()["listings"])


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
    assert not any(item["id"] == listing_id for item in active_resp.json()["listings"])

    inactive_resp = await client.get(
        "/api/users/me/listings?status=inactive", headers=headers
    )
    assert inactive_resp.status_code == 200
    assert any(item["id"] == listing_id for item in inactive_resp.json()["listings"])


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
    await _create_listing(client, token=seller_token, category_id=category.id)

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
    assert any(item["id"] == listing["id"] for item in resp.json()["listings"])


async def test_get_user_listings_hides_inactive(client, session_factory):
    category = await _create_category(session_factory, name="Electronics")
    token = await _register(client, email="u12@example.com", username="u12")
    listing = await _create_listing(client, token=token, category_id=category.id)

    resp = await client.get("/api/users/u12/listings")

    assert resp.status_code == 200
    assert not any(item["id"] == listing["id"] for item in resp.json()["listings"])


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
