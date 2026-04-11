import json
from uuid import UUID

from redis.asyncio import Redis

from .consts import PRESENCE_TTL
from .models import Message
from .schemas import MessageResponse


class ChatRedisManager:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    @staticmethod
    def conversation_channel(conversation_id: UUID) -> str:
        return f"chat:conversation:{conversation_id}"

    @staticmethod
    def presence_key(conversation_id: UUID, user_id: UUID) -> str:
        return f"chat:presence:{conversation_id}:{user_id}"

    async def publish_message(self, msg: Message) -> None:
        payload = MessageResponse.model_validate(msg).model_dump_json()
        await self._redis.publish(
            self.conversation_channel(msg.conversation_id), payload
        )

    async def publish_deletion(self, conversation_id: UUID, message_id: UUID) -> None:
        payload = json.dumps({"type": "message_deleted", "message_id": str(message_id)})
        await self._redis.publish(self.conversation_channel(conversation_id), payload)

    async def is_online(self, conversation_id: UUID, user_id: UUID) -> bool:
        return bool(
            await self._redis.exists(self.presence_key(conversation_id, user_id))
        )

    async def set_presence(self, conversation_id: UUID, user_id: UUID) -> None:
        await self._redis.setex(
            self.presence_key(conversation_id, user_id), PRESENCE_TTL, "1"
        )

    async def refresh_presence(self, conversation_id: UUID, user_id: UUID) -> None:
        await self._redis.setex(
            self.presence_key(conversation_id, user_id), PRESENCE_TTL, "1"
        )

    async def delete_presence(self, conversation_id: UUID, user_id: UUID) -> None:
        await self._redis.delete(self.presence_key(conversation_id, user_id))

    def pubsub(self):
        return self._redis.pubsub()
