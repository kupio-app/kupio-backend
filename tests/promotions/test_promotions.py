from sqlalchemy import update

from src.domains.categories.models import Category
from src.domains.promotions.models import PromotionPacket
from src.domains.promotions.enums import PromotionType
from src.domains.users.models import User
from src.domains.users.enums import UserRole
from tests.helpers.auth import auth_header, register_user
from tests.helpers.listings import activate_listing, create_category, create_listing


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
    return await create_category(session_factory, name=name, depth=0)


async def _create_listing(client, *, token: str, category_id: int) -> dict:
    return await create_listing(client, token=token, category_id=category_id)


async def _activate_listing(client, *, token: str, listing_id: str) -> None:
    await activate_listing(client, token=token, listing_id=listing_id)


async def _create_packet(
    session_factory,
    *,
    name: str = "Top Promotion",
    promotion_type: PromotionType = PromotionType.TOP,
    duration_days: int = 7,
    price: int = 1000,
    is_active: bool = True,
) -> PromotionPacket:
    async with session_factory() as session:
        packet = PromotionPacket(
            name=name,
            description="Test packet",
            type=promotion_type,
            duration_days=duration_days,
            price=price,
            is_active=is_active,
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


async def _make_moderator(session_factory, *, username: str) -> None:
    async with session_factory() as session:
        await session.execute(
            update(User)
            .where(User.username == username)
            .values(role=UserRole.MODERATOR)
        )
        await session.commit()


async def _purchase(client, *, token: str, listing_id: str, packet_id: int) -> dict:
    resp = await client.post(
        f"/api/listings/promotions/{listing_id}",
        headers=_auth_header(token),
        json={"packet_id": packet_id},
    )
    return resp


async def test_list_packets_returns_only_active(client, session_factory):
    await _create_packet(session_factory, name="Active Packet", is_active=True)
    await _create_packet(
        session_factory,
        name="Inactive Packet",
        promotion_type=PromotionType.HIGHLIGHT,
        is_active=False,
    )

    resp = await client.get("/api/promotions/packets")

    assert resp.status_code == 200
    names = [p["name"] for p in resp.json()]
    assert "Active Packet" in names
    assert "Inactive Packet" not in names


async def test_get_packet_by_id(client, session_factory):
    packet = await _create_packet(
        session_factory, name="VIP Packet", promotion_type=PromotionType.VIP
    )

    resp = await client.get(f"/api/promotions/packets/{packet.id}")

    assert resp.status_code == 200
    assert resp.json()["name"] == "VIP Packet"
    assert resp.json()["type"] == "vip"


async def test_get_packet_not_found_returns_404(client):
    resp = await client.get("/api/promotions/packets/99999")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Promotion packet not found"


async def test_create_packet_as_moderator(client, session_factory):
    token = await _register(client, email="mod@example.com", username="moduser")
    await _make_moderator(session_factory, username="moduser")

    resp = await client.post(
        "/api/promotions/packets",
        headers=_auth_header(token),
        json={
            "name": "Urgent Packet",
            "type": "urgent",
            "duration_days": 3,
            "price": 300,
        },
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Urgent Packet"
    assert body["type"] == "urgent"
    assert body["duration_days"] == 3
    assert body["price"] == 300
    assert body["is_active"] is True


async def test_create_packet_requires_moderator_role(client, session_factory):
    token = await _register(client, email="user@example.com", username="regularuser")

    resp = await client.post(
        "/api/promotions/packets",
        headers=_auth_header(token),
        json={"name": "Packet", "type": "top", "duration_days": 7, "price": 500},
    )

    assert resp.status_code == 403


async def test_create_packet_requires_auth(client):
    resp = await client.post(
        "/api/promotions/packets",
        json={"name": "Packet", "type": "top", "duration_days": 7, "price": 500},
    )

    assert resp.status_code == 401


async def test_update_packet_as_moderator(client, session_factory):
    token = await _register(client, email="mod2@example.com", username="moduser2")
    await _make_moderator(session_factory, username="moduser2")
    packet = await _create_packet(
        session_factory,
        name="Old Name",
        promotion_type=PromotionType.TOP,
        price=500,
    )

    resp = await client.patch(
        f"/api/promotions/packets/{packet.id}",
        headers=_auth_header(token),
        json={"name": "New Name", "price": 999, "is_active": False},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "New Name"
    assert body["price"] == 999
    assert body["is_active"] is False


async def test_update_packet_requires_moderator_role(client, session_factory):
    token = await _register(client, email="user2@example.com", username="user2")
    packet = await _create_packet(session_factory, name="Test Packet")

    resp = await client.patch(
        f"/api/promotions/packets/{packet.id}",
        headers=_auth_header(token),
        json={"name": "Hacked Name"},
    )

    assert resp.status_code == 403


async def test_purchase_promotion_success(client, session_factory):
    category = await _create_category(session_factory, name="Electronics")
    token = await _register(client, email="buyer@example.com", username="buyer")
    await _add_balance(session_factory, username="buyer", amount=5000)
    listing = await _create_listing(client, token=token, category_id=category.id)
    await _activate_listing(client, token=token, listing_id=listing["id"])
    packet = await _create_packet(
        session_factory, name="Top Pack", promotion_type=PromotionType.TOP, price=1000
    )

    resp = await _purchase(
        client, token=token, listing_id=listing["id"], packet_id=packet.id
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["listing_id"] == listing["id"]
    assert body["status"] == "active"
    assert body["packet"]["id"] == packet.id
    assert body["packet"]["type"] == "top"


async def test_purchase_deducts_balance_and_creates_transaction(
    client, session_factory
):
    category = await _create_category(session_factory, name="Electronics")
    token = await _register(client, email="buyer2@example.com", username="buyer2")
    await _add_balance(session_factory, username="buyer2", amount=5000)
    listing = await _create_listing(client, token=token, category_id=category.id)
    await _activate_listing(client, token=token, listing_id=listing["id"])
    packet = await _create_packet(
        session_factory, name="Top Pack2", promotion_type=PromotionType.TOP, price=1000
    )

    await _purchase(client, token=token, listing_id=listing["id"], packet_id=packet.id)

    tx_resp = await client.get(
        "/api/payments/transactions", headers=_auth_header(token)
    )
    assert tx_resp.status_code == 200
    transactions = tx_resp.json()
    assert len(transactions) == 1
    assert transactions[0]["amount"] == -1000
    assert transactions[0]["type"] == "debit"


async def test_purchase_inactive_listing_returns_400(client, session_factory):
    category = await _create_category(session_factory, name="Electronics")
    token = await _register(client, email="buyer3@example.com", username="buyer3")
    await _add_balance(session_factory, username="buyer3", amount=5000)
    listing = await _create_listing(client, token=token, category_id=category.id)
    # listing stays inactive
    packet = await _create_packet(session_factory, name="Pack3", price=1000)

    resp = await _purchase(
        client, token=token, listing_id=listing["id"], packet_id=packet.id
    )

    assert resp.status_code == 400
    assert resp.json()["detail"] == "Only active listings can be promoted"


async def test_purchase_inactive_packet_returns_400(client, session_factory):
    category = await _create_category(session_factory, name="Electronics")
    token = await _register(client, email="buyer4@example.com", username="buyer4")
    await _add_balance(session_factory, username="buyer4", amount=5000)
    listing = await _create_listing(client, token=token, category_id=category.id)
    await _activate_listing(client, token=token, listing_id=listing["id"])
    packet = await _create_packet(
        session_factory, name="Inactive Pack", price=1000, is_active=False
    )

    resp = await _purchase(
        client, token=token, listing_id=listing["id"], packet_id=packet.id
    )

    assert resp.status_code == 400
    assert resp.json()["detail"] == "Promotion packet is not available"


async def test_purchase_insufficient_balance_returns_400(client, session_factory):
    category = await _create_category(session_factory, name="Electronics")
    token = await _register(client, email="buyer5@example.com", username="buyer5")
    # balance stays 0
    listing = await _create_listing(client, token=token, category_id=category.id)
    await _activate_listing(client, token=token, listing_id=listing["id"])
    packet = await _create_packet(session_factory, name="Expensive Pack", price=10000)

    resp = await _purchase(
        client, token=token, listing_id=listing["id"], packet_id=packet.id
    )

    assert resp.status_code == 400
    assert resp.json()["detail"] == "Insufficient balance"


async def test_purchase_duplicate_promotion_type_returns_409(client, session_factory):
    category = await _create_category(session_factory, name="Electronics")
    token = await _register(client, email="buyer6@example.com", username="buyer6")
    await _add_balance(session_factory, username="buyer6", amount=10000)
    listing = await _create_listing(client, token=token, category_id=category.id)
    await _activate_listing(client, token=token, listing_id=listing["id"])
    packet = await _create_packet(
        session_factory, name="Top Pack6", promotion_type=PromotionType.TOP, price=1000
    )

    first = await _purchase(
        client, token=token, listing_id=listing["id"], packet_id=packet.id
    )
    assert first.status_code == 201

    second = await _purchase(
        client, token=token, listing_id=listing["id"], packet_id=packet.id
    )
    assert second.status_code == 409
    assert "already exists" in second.json()["detail"]


async def test_purchase_different_types_on_same_listing_succeed(
    client, session_factory
):
    category = await _create_category(session_factory, name="Electronics")
    token = await _register(client, email="buyer7@example.com", username="buyer7")
    await _add_balance(session_factory, username="buyer7", amount=10000)
    listing = await _create_listing(client, token=token, category_id=category.id)
    await _activate_listing(client, token=token, listing_id=listing["id"])
    top_packet = await _create_packet(
        session_factory, name="Top Pack7", promotion_type=PromotionType.TOP, price=1000
    )
    highlight_packet = await _create_packet(
        session_factory,
        name="Highlight Pack7",
        promotion_type=PromotionType.HIGHLIGHT,
        price=1000,
    )

    r1 = await _purchase(
        client, token=token, listing_id=listing["id"], packet_id=top_packet.id
    )
    r2 = await _purchase(
        client, token=token, listing_id=listing["id"], packet_id=highlight_packet.id
    )

    assert r1.status_code == 201
    assert r2.status_code == 201


async def test_purchase_by_non_owner_returns_403(client, session_factory):
    category = await _create_category(session_factory, name="Electronics")
    owner_token = await _register(client, email="owner@example.com", username="owner")
    other_token = await _register(
        client, email="other@example.com", username="other", device_id="d2"
    )
    listing = await _create_listing(client, token=owner_token, category_id=category.id)
    await _activate_listing(client, token=owner_token, listing_id=listing["id"])
    await _add_balance(session_factory, username="other", amount=5000)
    packet = await _create_packet(session_factory, name="Top Pack8", price=1000)

    resp = await _purchase(
        client, token=other_token, listing_id=listing["id"], packet_id=packet.id
    )

    assert resp.status_code == 403


async def test_purchase_unknown_packet_returns_404(client, session_factory):
    category = await _create_category(session_factory, name="Electronics")
    token = await _register(client, email="buyer8@example.com", username="buyer8")
    await _add_balance(session_factory, username="buyer8", amount=5000)
    listing = await _create_listing(client, token=token, category_id=category.id)
    await _activate_listing(client, token=token, listing_id=listing["id"])

    resp = await _purchase(
        client, token=token, listing_id=listing["id"], packet_id=99999
    )

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Promotion packet not found"


async def test_purchase_requires_auth(client, session_factory):
    category = await _create_category(session_factory, name="Electronics")
    token = await _register(client, email="buyer9@example.com", username="buyer9")
    listing = await _create_listing(client, token=token, category_id=category.id)

    resp = await client.post(
        f"/api/listings/promotions/{listing['id']}",
        json={"packet_id": 1},
    )

    assert resp.status_code == 401


async def test_list_listing_promotions_returns_active(client, session_factory):
    category = await _create_category(session_factory, name="Electronics")
    token = await _register(client, email="seller@example.com", username="seller")
    await _add_balance(session_factory, username="seller", amount=5000)
    listing = await _create_listing(client, token=token, category_id=category.id)
    await _activate_listing(client, token=token, listing_id=listing["id"])
    packet = await _create_packet(
        session_factory,
        name="Top PackList",
        promotion_type=PromotionType.TOP,
        price=1000,
    )

    await _purchase(client, token=token, listing_id=listing["id"], packet_id=packet.id)

    resp = await client.get(
        f"/api/listings/promotions/{listing['id']}", headers=_auth_header(token)
    )

    assert resp.status_code == 200
    promotions = resp.json()
    assert len(promotions) == 1
    assert promotions[0]["status"] == "active"
    assert promotions[0]["listing_id"] == listing["id"]


async def test_list_listing_promotions_empty_before_purchase(client, session_factory):
    category = await _create_category(session_factory, name="Electronics")
    token = await _register(client, email="seller2@example.com", username="seller2")
    listing = await _create_listing(client, token=token, category_id=category.id)
    await _activate_listing(client, token=token, listing_id=listing["id"])

    resp = await client.get(
        f"/api/listings/promotions/{listing['id']}", headers=_auth_header(token)
    )

    assert resp.status_code == 200
    assert resp.json() == []


async def test_get_my_promotions_returns_purchased(client, session_factory):
    category = await _create_category(session_factory, name="Electronics")
    token = await _register(client, email="mypromo@example.com", username="mypromo")
    await _add_balance(session_factory, username="mypromo", amount=5000)
    listing = await _create_listing(client, token=token, category_id=category.id)
    await _activate_listing(client, token=token, listing_id=listing["id"])
    packet = await _create_packet(
        session_factory,
        name="My Promo Pack",
        promotion_type=PromotionType.HIGHLIGHT,
        price=500,
    )

    await _purchase(client, token=token, listing_id=listing["id"], packet_id=packet.id)

    resp = await client.get("/api/users/me/promotions", headers=_auth_header(token))

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["promotions"]) == 1
    assert body["next_cursor"] is None
    assert body["promotions"][0]["status"] == "active"


async def test_get_my_promotions_empty_for_new_user(client, session_factory):
    token = await _register(client, email="nopromo@example.com", username="nopromo")

    resp = await client.get("/api/users/me/promotions", headers=_auth_header(token))

    assert resp.status_code == 200
    body = resp.json()
    assert body["promotions"] == []
    assert body["next_cursor"] is None


async def test_get_my_promotions_requires_auth(client):
    resp = await client.get("/api/users/me/promotions")

    assert resp.status_code == 401


async def test_list_transactions_empty_before_purchase(client, session_factory):
    token = await _register(client, email="tx@example.com", username="txuser")

    resp = await client.get("/api/payments/transactions", headers=_auth_header(token))

    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_transactions_requires_auth(client):
    resp = await client.get("/api/payments/transactions")

    assert resp.status_code == 401


async def test_list_transactions_isolated_per_user(client, session_factory):
    category = await _create_category(session_factory, name="Electronics")
    token_a = await _register(client, email="usera@example.com", username="usera")
    token_b = await _register(
        client, email="userb@example.com", username="userb", device_id="d2"
    )
    await _add_balance(session_factory, username="usera", amount=5000)
    listing = await _create_listing(client, token=token_a, category_id=category.id)
    await _activate_listing(client, token=token_a, listing_id=listing["id"])
    packet = await _create_packet(session_factory, name="Isolation Pack", price=1000)

    await _purchase(
        client, token=token_a, listing_id=listing["id"], packet_id=packet.id
    )

    resp_b = await client.get(
        "/api/payments/transactions", headers=_auth_header(token_b)
    )
    assert resp_b.json() == []

    resp_a = await client.get(
        "/api/payments/transactions", headers=_auth_header(token_a)
    )
    assert len(resp_a.json()) == 1
