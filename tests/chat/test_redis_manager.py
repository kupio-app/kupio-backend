from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.domains.chat.redis import ChatRedisManager


class FakeRedis:
    def __init__(self) -> None:
        self.published = []
        self.setex_calls = []
        self.deleted = []
        self.exists_calls = []

    async def publish(self, channel, payload):
        self.published.append((channel, payload))

    async def setex(self, key, ttl, value):
        self.setex_calls.append((key, ttl, value))

    async def delete(self, key):
        self.deleted.append(key)

    async def exists(self, key):
        self.exists_calls.append(key)
        return 1

    def pubsub(self):
        return SimpleNamespace()


@pytest.mark.asyncio
async def test_chat_redis_manager_presence_and_publish():
    redis = FakeRedis()
    manager = ChatRedisManager(redis)
    conversation_id = uuid4()
    user_id = uuid4()

    await manager.publish_typing(conversation_id, user_id)
    await manager.publish_read(conversation_id, user_id)
    await manager.set_presence(conversation_id, user_id)
    await manager.refresh_presence(conversation_id, user_id)
    await manager.delete_presence(conversation_id, user_id)

    assert redis.published
    assert redis.setex_calls
    assert redis.deleted

    online = await manager.is_online(conversation_id, user_id)
    assert online is True
