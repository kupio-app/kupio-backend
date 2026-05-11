import uuid
from unittest.mock import AsyncMock

import pytest_asyncio

import src.domains.chat.service as chat_service_module
from src.domains.categories.models import Category
from src.domains.chat.dependencies import get_chat_redis
from src.domains.chat.redis import ChatRedisManager
from tests.helpers.auth import auth_header, register_user
from tests.helpers.listings import create_category


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
    resp = await client.post(
        "/api/listings",
        headers=_auth_header(token),
        json={
            "title": "Test listing for chat",
            "description": "A listing used in chat integration tests, good condition, no defects.",
            "price": 1000,
            "is_free": False,
            "is_tradable": False,
            "currency": "usd",
            "category_id": category_id,
        },
    )
    assert resp.status_code == 200
    return resp.json()


async def _start_conversation(client, *, token: str, listing_id: str) -> dict:
    resp = await client.post(
        "/api/chat/conversations",
        headers=_auth_header(token),
        params={"listing_id": listing_id},
    )
    assert resp.status_code == 201
    return resp.json()


@pytest_asyncio.fixture(autouse=True)
async def mock_chat_dependencies(app, monkeypatch):
    """Mock ChatRedisManager and the FCM push worker for all chat tests."""
    fake_redis = AsyncMock(spec=ChatRedisManager)
    fake_redis.is_online.return_value = False

    app.dependency_overrides[get_chat_redis] = lambda: fake_redis

    mock_task = AsyncMock()
    mock_task.enqueue = AsyncMock()
    monkeypatch.setattr(chat_service_module, "send_fcm_push", mock_task)

    yield fake_redis

    app.dependency_overrides.pop(get_chat_redis, None)


async def test_start_conversation_creates_new(client, session_factory):
    category = await _create_category(session_factory, name="Chat-Electronics")
    seller_token = await _register(client, email="seller1@chat.com", username="seller1")
    buyer_token = await _register(client, email="buyer1@chat.com", username="buyer1")

    listing = await _create_listing(client, token=seller_token, category_id=category.id)

    resp = await client.post(
        "/api/chat/conversations",
        headers=_auth_header(buyer_token),
        params={"listing_id": listing["id"]},
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["listing_id"] == listing["id"]
    assert "id" in body
    assert "created_at" in body


async def test_start_conversation_returns_existing_on_duplicate(
    client, session_factory
):
    category = await _create_category(session_factory, name="Chat-Electronics2")
    seller_token = await _register(client, email="seller2@chat.com", username="seller2")
    buyer_token = await _register(client, email="buyer2@chat.com", username="buyer2")
    listing = await _create_listing(client, token=seller_token, category_id=category.id)

    first = await _start_conversation(
        client, token=buyer_token, listing_id=listing["id"]
    )
    second_resp = await client.post(
        "/api/chat/conversations",
        headers=_auth_header(buyer_token),
        params={"listing_id": listing["id"]},
    )

    assert second_resp.status_code == 201
    assert second_resp.json()["id"] == first["id"]


async def test_start_conversation_own_listing_returns_400(client, session_factory):
    category = await _create_category(session_factory, name="Chat-Electronics3")
    seller_token = await _register(client, email="seller3@chat.com", username="seller3")
    listing = await _create_listing(client, token=seller_token, category_id=category.id)

    resp = await client.post(
        "/api/chat/conversations",
        headers=_auth_header(seller_token),
        params={"listing_id": listing["id"]},
    )

    assert resp.status_code == 400
    assert "own listing" in resp.json()["detail"].lower()


async def test_start_conversation_unauthenticated_returns_401(client, session_factory):
    category = await _create_category(session_factory, name="Chat-Electronics4")
    seller_token = await _register(client, email="seller4@chat.com", username="seller4")
    listing = await _create_listing(client, token=seller_token, category_id=category.id)

    resp = await client.post(
        "/api/chat/conversations",
        params={"listing_id": listing["id"]},
    )

    assert resp.status_code == 401


async def test_start_conversation_listing_not_found_returns_404(client):
    buyer_token = await _register(client, email="buyer5@chat.com", username="buyer5")

    resp = await client.post(
        "/api/chat/conversations",
        headers=_auth_header(buyer_token),
        params={"listing_id": str(uuid.uuid4())},
    )

    assert resp.status_code == 404


async def test_get_conversation_returns_200_for_participant(client, session_factory):
    category = await _create_category(session_factory, name="Chat-Electronics6")
    seller_token = await _register(client, email="seller6@chat.com", username="seller6")
    buyer_token = await _register(client, email="buyer6@chat.com", username="buyer6")
    listing = await _create_listing(client, token=seller_token, category_id=category.id)
    conv = await _start_conversation(
        client, token=buyer_token, listing_id=listing["id"]
    )

    resp = await client.get(
        f"/api/chat/conversations/{conv['id']}",
        headers=_auth_header(buyer_token),
    )

    assert resp.status_code == 200
    assert resp.json()["id"] == conv["id"]


async def test_get_conversation_accessible_by_seller_too(client, session_factory):
    category = await _create_category(session_factory, name="Chat-Electronics7")
    seller_token = await _register(client, email="seller7@chat.com", username="seller7")
    buyer_token = await _register(client, email="buyer7@chat.com", username="buyer7")
    listing = await _create_listing(client, token=seller_token, category_id=category.id)
    conv = await _start_conversation(
        client, token=buyer_token, listing_id=listing["id"]
    )

    resp = await client.get(
        f"/api/chat/conversations/{conv['id']}",
        headers=_auth_header(seller_token),
    )

    assert resp.status_code == 200


async def test_get_conversation_non_participant_returns_403(client, session_factory):
    category = await _create_category(session_factory, name="Chat-Electronics8")
    seller_token = await _register(client, email="seller8@chat.com", username="seller8")
    buyer_token = await _register(client, email="buyer8@chat.com", username="buyer8")
    other_token = await _register(client, email="other8@chat.com", username="other8")
    listing = await _create_listing(client, token=seller_token, category_id=category.id)
    conv = await _start_conversation(
        client, token=buyer_token, listing_id=listing["id"]
    )

    resp = await client.get(
        f"/api/chat/conversations/{conv['id']}",
        headers=_auth_header(other_token),
    )

    assert resp.status_code == 403


async def test_get_conversation_not_found_returns_404(client):
    token = await _register(client, email="user9@chat.com", username="user9")

    resp = await client.get(
        f"/api/chat/conversations/{uuid.uuid4()}",
        headers=_auth_header(token),
    )

    assert resp.status_code == 404


async def test_list_conversations_as_buyer(client, session_factory):
    category = await _create_category(session_factory, name="Chat-Electronics10")
    seller_token = await _register(
        client, email="seller10@chat.com", username="seller10"
    )
    buyer_token = await _register(client, email="buyer10@chat.com", username="buyer10")

    listing1 = await _create_listing(
        client, token=seller_token, category_id=category.id
    )
    listing2 = await _create_listing(
        client, token=seller_token, category_id=category.id
    )
    await _start_conversation(client, token=buyer_token, listing_id=listing1["id"])
    await _start_conversation(client, token=buyer_token, listing_id=listing2["id"])

    resp = await client.get(
        "/api/chat/conversations",
        headers=_auth_header(buyer_token),
        params={"role": "buyer"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["conversations"]) == 2


async def test_list_conversations_as_seller(client, session_factory):
    category = await _create_category(session_factory, name="Chat-Electronics11")
    seller_token = await _register(
        client, email="seller11@chat.com", username="seller11"
    )
    buyer1_token = await _register(
        client, email="buyer11a@chat.com", username="buyer11a"
    )
    buyer2_token = await _register(
        client, email="buyer11b@chat.com", username="buyer11b"
    )
    listing = await _create_listing(client, token=seller_token, category_id=category.id)

    await _start_conversation(client, token=buyer1_token, listing_id=listing["id"])
    await _start_conversation(client, token=buyer2_token, listing_id=listing["id"])

    resp = await client.get(
        "/api/chat/conversations",
        headers=_auth_header(seller_token),
        params={"role": "seller"},
    )

    assert resp.status_code == 200
    assert len(resp.json()["conversations"]) == 2


async def test_list_conversations_only_own(client, session_factory):
    """A buyer should not see another buyer's conversations."""
    category = await _create_category(session_factory, name="Chat-Electronics12")
    seller_token = await _register(
        client, email="seller12@chat.com", username="seller12"
    )
    buyer1_token = await _register(
        client, email="buyer12a@chat.com", username="buyer12a"
    )
    buyer2_token = await _register(
        client, email="buyer12b@chat.com", username="buyer12b"
    )
    listing = await _create_listing(client, token=seller_token, category_id=category.id)

    await _start_conversation(client, token=buyer1_token, listing_id=listing["id"])

    resp = await client.get(
        "/api/chat/conversations",
        headers=_auth_header(buyer2_token),
        params={"role": "buyer"},
    )

    assert resp.status_code == 200
    assert resp.json()["conversations"] == []


async def test_list_conversations_requires_auth(client):
    resp = await client.get(
        "/api/chat/conversations",
        params={"role": "buyer"},
    )
    assert resp.status_code == 401


async def test_list_conversations_next_cursor_present_when_full_page(
    client, session_factory
):
    category = await _create_category(session_factory, name="Chat-Electronics13")
    seller_token = await _register(
        client, email="seller13@chat.com", username="seller13"
    )
    buyer_token = await _register(client, email="buyer13@chat.com", username="buyer13")

    for i in range(3):
        listing = await _create_listing(
            client, token=seller_token, category_id=category.id
        )
        await _start_conversation(client, token=buyer_token, listing_id=listing["id"])

    resp = await client.get(
        "/api/chat/conversations",
        headers=_auth_header(buyer_token),
        params={"role": "buyer", "limit": 2},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["conversations"]) == 2
    assert body["next_cursor"] is not None


async def test_send_message_creates_message(client, session_factory):
    category = await _create_category(session_factory, name="Chat-Electronics14")
    seller_token = await _register(
        client, email="seller14@chat.com", username="seller14"
    )
    buyer_token = await _register(client, email="buyer14@chat.com", username="buyer14")
    listing = await _create_listing(client, token=seller_token, category_id=category.id)
    conv = await _start_conversation(
        client, token=buyer_token, listing_id=listing["id"]
    )

    resp = await client.post(
        f"/api/chat/conversations/{conv['id']}/messages",
        headers=_auth_header(buyer_token),
        json={"body": "Hello, is this still available?"},
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["content"] == "Hello, is this still available?"
    assert body["is_deleted"] is False
    assert body["conversation_id"] == conv["id"]


async def test_send_message_non_participant_returns_403(client, session_factory):
    category = await _create_category(session_factory, name="Chat-Electronics15")
    seller_token = await _register(
        client, email="seller15@chat.com", username="seller15"
    )
    buyer_token = await _register(client, email="buyer15@chat.com", username="buyer15")
    other_token = await _register(client, email="other15@chat.com", username="other15")
    listing = await _create_listing(client, token=seller_token, category_id=category.id)
    conv = await _start_conversation(
        client, token=buyer_token, listing_id=listing["id"]
    )

    resp = await client.post(
        f"/api/chat/conversations/{conv['id']}/messages",
        headers=_auth_header(other_token),
        json={"body": "I should not be able to send this"},
    )

    assert resp.status_code == 403


async def test_send_message_empty_body_returns_422(client, session_factory):
    category = await _create_category(session_factory, name="Chat-Electronics16")
    seller_token = await _register(
        client, email="seller16@chat.com", username="seller16"
    )
    buyer_token = await _register(client, email="buyer16@chat.com", username="buyer16")
    listing = await _create_listing(client, token=seller_token, category_id=category.id)
    conv = await _start_conversation(
        client, token=buyer_token, listing_id=listing["id"]
    )

    resp = await client.post(
        f"/api/chat/conversations/{conv['id']}/messages",
        headers=_auth_header(buyer_token),
        json={"body": ""},
    )

    assert resp.status_code == 422


async def test_send_message_body_too_long_returns_422(client, session_factory):
    category = await _create_category(session_factory, name="Chat-Electronics17")
    seller_token = await _register(
        client, email="seller17@chat.com", username="seller17"
    )
    buyer_token = await _register(client, email="buyer17@chat.com", username="buyer17")
    listing = await _create_listing(client, token=seller_token, category_id=category.id)
    conv = await _start_conversation(
        client, token=buyer_token, listing_id=listing["id"]
    )

    resp = await client.post(
        f"/api/chat/conversations/{conv['id']}/messages",
        headers=_auth_header(buyer_token),
        json={"body": "x" * 4001},
    )

    assert resp.status_code == 422


async def test_seller_can_reply(client, session_factory):
    category = await _create_category(session_factory, name="Chat-Electronics18")
    seller_token = await _register(
        client, email="seller18@chat.com", username="seller18"
    )
    buyer_token = await _register(client, email="buyer18@chat.com", username="buyer18")
    listing = await _create_listing(client, token=seller_token, category_id=category.id)
    conv = await _start_conversation(
        client, token=buyer_token, listing_id=listing["id"]
    )

    resp = await client.post(
        f"/api/chat/conversations/{conv['id']}/messages",
        headers=_auth_header(seller_token),
        json={"body": "Yes, still available!"},
    )

    assert resp.status_code == 201
    assert resp.json()["content"] == "Yes, still available!"


async def test_list_messages_returns_sent_messages(client, session_factory):
    category = await _create_category(session_factory, name="Chat-Electronics19")
    seller_token = await _register(
        client, email="seller19@chat.com", username="seller19"
    )
    buyer_token = await _register(client, email="buyer19@chat.com", username="buyer19")
    listing = await _create_listing(client, token=seller_token, category_id=category.id)
    conv = await _start_conversation(
        client, token=buyer_token, listing_id=listing["id"]
    )

    await client.post(
        f"/api/chat/conversations/{conv['id']}/messages",
        headers=_auth_header(buyer_token),
        json={"body": "Message 1"},
    )
    await client.post(
        f"/api/chat/conversations/{conv['id']}/messages",
        headers=_auth_header(seller_token),
        json={"body": "Message 2"},
    )

    resp = await client.get(
        f"/api/chat/conversations/{conv['id']}/messages",
        headers=_auth_header(buyer_token),
    )

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["messages"]) == 2


async def test_list_messages_non_participant_returns_403(client, session_factory):
    category = await _create_category(session_factory, name="Chat-Electronics20")
    seller_token = await _register(
        client, email="seller20@chat.com", username="seller20"
    )
    buyer_token = await _register(client, email="buyer20@chat.com", username="buyer20")
    other_token = await _register(client, email="other20@chat.com", username="other20")
    listing = await _create_listing(client, token=seller_token, category_id=category.id)
    conv = await _start_conversation(
        client, token=buyer_token, listing_id=listing["id"]
    )

    resp = await client.get(
        f"/api/chat/conversations/{conv['id']}/messages",
        headers=_auth_header(other_token),
    )

    assert resp.status_code == 403


async def test_list_messages_next_cursor_present_when_full_page(
    client, session_factory
):
    category = await _create_category(session_factory, name="Chat-Electronics21")
    seller_token = await _register(
        client, email="seller21@chat.com", username="seller21"
    )
    buyer_token = await _register(client, email="buyer21@chat.com", username="buyer21")
    listing = await _create_listing(client, token=seller_token, category_id=category.id)
    conv = await _start_conversation(
        client, token=buyer_token, listing_id=listing["id"]
    )

    for i in range(3):
        await client.post(
            f"/api/chat/conversations/{conv['id']}/messages",
            headers=_auth_header(buyer_token),
            json={"body": f"Message {i}"},
        )

    resp = await client.get(
        f"/api/chat/conversations/{conv['id']}/messages",
        headers=_auth_header(buyer_token),
        params={"limit": 2},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["messages"]) == 2
    assert body["next_cursor"] is not None


async def test_delete_message_soft_deletes(client, session_factory):
    category = await _create_category(session_factory, name="Chat-Electronics22")
    seller_token = await _register(
        client, email="seller22@chat.com", username="seller22"
    )
    buyer_token = await _register(client, email="buyer22@chat.com", username="buyer22")
    listing = await _create_listing(client, token=seller_token, category_id=category.id)
    conv = await _start_conversation(
        client, token=buyer_token, listing_id=listing["id"]
    )

    msg_resp = await client.post(
        f"/api/chat/conversations/{conv['id']}/messages",
        headers=_auth_header(buyer_token),
        json={"body": "Delete me"},
    )
    msg_id = msg_resp.json()["id"]

    delete_resp = await client.delete(
        f"/api/chat/conversations/{conv['id']}/messages/{msg_id}",
        headers=_auth_header(buyer_token),
    )
    assert delete_resp.status_code == 204

    msgs = await client.get(
        f"/api/chat/conversations/{conv['id']}/messages",
        headers=_auth_header(buyer_token),
    )
    deleted = next(m for m in msgs.json()["messages"] if m["id"] == msg_id)
    assert deleted["is_deleted"] is True
    assert deleted["content"] is None


async def test_delete_foreign_message_returns_403(client, session_factory):
    category = await _create_category(session_factory, name="Chat-Electronics23")
    seller_token = await _register(
        client, email="seller23@chat.com", username="seller23"
    )
    buyer_token = await _register(client, email="buyer23@chat.com", username="buyer23")
    listing = await _create_listing(client, token=seller_token, category_id=category.id)
    conv = await _start_conversation(
        client, token=buyer_token, listing_id=listing["id"]
    )

    msg_resp = await client.post(
        f"/api/chat/conversations/{conv['id']}/messages",
        headers=_auth_header(buyer_token),
        json={"body": "Buyer's message"},
    )
    msg_id = msg_resp.json()["id"]

    resp = await client.delete(
        f"/api/chat/conversations/{conv['id']}/messages/{msg_id}",
        headers=_auth_header(seller_token),
    )

    assert resp.status_code == 403


async def test_delete_message_not_found_returns_404(client, session_factory):
    category = await _create_category(session_factory, name="Chat-Electronics24")
    seller_token = await _register(
        client, email="seller24@chat.com", username="seller24"
    )
    buyer_token = await _register(client, email="buyer24@chat.com", username="buyer24")
    listing = await _create_listing(client, token=seller_token, category_id=category.id)
    conv = await _start_conversation(
        client, token=buyer_token, listing_id=listing["id"]
    )

    resp = await client.delete(
        f"/api/chat/conversations/{conv['id']}/messages/{uuid.uuid4()}",
        headers=_auth_header(buyer_token),
    )

    assert resp.status_code == 404


async def test_delete_message_from_wrong_conversation_returns_404(
    client, session_factory
):
    """A message from conversation A cannot be deleted via conversation B's URL."""
    category = await _create_category(session_factory, name="Chat-Electronics25")
    seller_token = await _register(
        client, email="seller25@chat.com", username="seller25"
    )
    buyer_token = await _register(client, email="buyer25@chat.com", username="buyer25")

    listing1 = await _create_listing(
        client, token=seller_token, category_id=category.id
    )
    listing2 = await _create_listing(
        client, token=seller_token, category_id=category.id
    )
    conv1 = await _start_conversation(
        client, token=buyer_token, listing_id=listing1["id"]
    )
    conv2 = await _start_conversation(
        client, token=buyer_token, listing_id=listing2["id"]
    )

    msg_resp = await client.post(
        f"/api/chat/conversations/{conv1['id']}/messages",
        headers=_auth_header(buyer_token),
        json={"body": "Message in conv1"},
    )
    msg_id = msg_resp.json()["id"]

    resp = await client.delete(
        f"/api/chat/conversations/{conv2['id']}/messages/{msg_id}",
        headers=_auth_header(buyer_token),
    )

    assert resp.status_code == 404
