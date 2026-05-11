import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import WebSocketDisconnect

from src.domains.chat.ws.handler import ChatWebSocketSession


class DummyWebSocket:
    def __init__(self, messages):
        self._messages = list(messages)
        self.sent = []
        self.closed = None
        self.app = SimpleNamespace(state=SimpleNamespace())

    async def receive_text(self):
        if not self._messages:
            raise WebSocketDisconnect()
        return self._messages.pop(0)

    async def send_text(self, text):
        self.sent.append(text)

    async def close(self, code):
        self.closed = code


@pytest.mark.asyncio
async def test_receive_token_invalid_payload_closes():
    ws = DummyWebSocket([json.dumps({"type": "auth", "token": ""})])
    session = ChatWebSocketSession(ws, uuid4(), None)

    errors = {}

    async def _close(msg, code):
        errors["code"] = code

    session._close_with_error = _close  # type: ignore[assignment]

    token = await session._receive_token()

    assert token is None
    assert errors["code"] == 4001


@pytest.mark.asyncio
async def test_receive_token_invalid_json_closes():
    ws = DummyWebSocket(["{bad-json"])
    session = ChatWebSocketSession(ws, uuid4(), None)

    errors = {}

    async def _close(msg, code):
        errors["code"] = code

    session._close_with_error = _close  # type: ignore[assignment]

    token = await session._receive_token()

    assert token is None
    assert errors["code"] == 4001


@pytest.mark.asyncio
async def test_receive_token_disconnect_returns_none():
    ws = DummyWebSocket([])
    session = ChatWebSocketSession(ws, uuid4(), None)

    token = await session._receive_token()

    assert token is None


@pytest.mark.asyncio
async def test_maybe_mark_read_skips_bad_json():
    ws = DummyWebSocket([])
    session = ChatWebSocketSession(ws, uuid4(), None)
    session._user_id = uuid4()

    called = {"count": 0}

    async def _mark_read():
        called["count"] += 1

    session._mark_read_silently = _mark_read  # type: ignore[assignment]

    await session._maybe_mark_read("{bad")

    assert called["count"] == 0


@pytest.mark.asyncio
async def test_maybe_mark_read_marks_when_other_user_message():
    ws = DummyWebSocket([])
    session = ChatWebSocketSession(ws, uuid4(), None)
    session._user_id = uuid4()

    called = {"count": 0}

    async def _mark_read():
        called["count"] += 1

    session._mark_read_silently = _mark_read  # type: ignore[assignment]

    payload = json.dumps(
        {"type": "new_message", "sender_id": str(uuid4()), "id": str(uuid4())}
    )
    await session._maybe_mark_read(payload)

    assert called["count"] == 1


@pytest.mark.asyncio
async def test_maybe_mark_read_skips_own_message():
    ws = DummyWebSocket([])
    session = ChatWebSocketSession(ws, uuid4(), None)
    session._user_id = uuid4()

    called = {"count": 0}

    async def _mark_read():
        called["count"] += 1

    session._mark_read_silently = _mark_read  # type: ignore[assignment]

    payload = json.dumps(
        {"type": "new_message", "sender_id": str(session._user_id), "id": str(uuid4())}
    )
    await session._maybe_mark_read(payload)

    assert called["count"] == 0


@pytest.mark.asyncio
async def test_receive_client_messages_handles_ping_and_typing(monkeypatch):
    ws = DummyWebSocket([json.dumps({"type": "ping"}), json.dumps({"type": "typing"})])
    session = ChatWebSocketSession(ws, uuid4(), None)
    session._user_id = uuid4()

    class FakeChatRedis:
        def __init__(self):
            self.typing = []

        async def publish_typing(self, conversation_id, user_id):
            self.typing.append((conversation_id, user_id))

    fake_redis = FakeChatRedis()
    monkeypatch.setattr(
        ChatWebSocketSession, "chat_redis", property(lambda self: fake_redis)
    )

    await session._receive_client_messages()

    assert fake_redis.typing
    assert ws.sent
