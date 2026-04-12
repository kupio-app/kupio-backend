import asyncio
import json
import logging
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect
from jose import ExpiredSignatureError, JWTError
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.config import get_config
from src.core.database.repositories import Repositories
from src.core.security import decode_access_token

from ..consts import PRESENCE_TTL, WS_AUTH_TIMEOUT
from ..redis import ChatRedisManager
from ..schemas import MessageResponse
from .messages import WsAuthOkMessage, WsErrorMessage, WsPongMessage

logger = logging.getLogger(__name__)


async def handle_chat_ws(
    websocket: WebSocket,
    conversation_id: UUID,
    last_message_id: UUID | None,
) -> None:
    session = ChatWebSocketSession(
        websocket=websocket,
        conversation_id=conversation_id,
        last_message_id=last_message_id,
    )
    await session.run()


class ChatWebSocketSession:
    def __init__(
        self,
        websocket: WebSocket,
        conversation_id: UUID,
        last_message_id: UUID | None,
    ) -> None:
        self.websocket = websocket
        self.conversation_id = conversation_id
        self.last_message_id = last_message_id
        self._user_id: UUID | None = None  # set after successful auth

    @property
    def chat_redis(self) -> ChatRedisManager:
        return ChatRedisManager(self.websocket.app.state.redis)

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        return self.websocket.app.state.db_session_factory

    async def run(self) -> None:
        await self.websocket.accept()

        user_id = await self._authenticate()
        if user_id is None:
            return

        authorized = await self._authorize_and_init(user_id)
        if not authorized:
            return

        await self._run_message_loop()

    async def _authenticate(self) -> UUID | None:
        """Read the auth message and return the validated user_id, or close and return None."""
        token = await self._receive_token()
        if token is None:
            return None

        return await self._decode_token(token)

    async def _receive_token(self) -> str | None:
        try:
            raw = await asyncio.wait_for(
                self.websocket.receive_text(), timeout=WS_AUTH_TIMEOUT
            )
            msg = json.loads(raw)
            if msg.get("type") != "auth" or not msg.get("token"):
                await self._close_with_error(WsErrorMessage(code="invalid_token"), 4001)
                return None

            return msg["token"]
        except asyncio.TimeoutError:
            await self._close_with_error(WsErrorMessage(code="auth_timeout"), 4001)
            return None
        except WebSocketDisconnect:
            return None
        except json.JSONDecodeError:
            await self._close_with_error(WsErrorMessage(code="invalid_token"), 4001)
            return None

    async def _decode_token(self, token: str) -> UUID | None:
        config = get_config()
        try:
            user_id_str = decode_access_token(token=token, config=config.auth)
            return UUID(user_id_str)
        except ExpiredSignatureError:
            await self._close_with_error(WsErrorMessage(code="token_expired"), 4001)
            return None
        except JWTError, ValueError:
            await self._close_with_error(WsErrorMessage(code="invalid_token"), 4001)
            return None

    async def _authorize_and_init(self, user_id: UUID) -> bool:
        """
        Verify the user is a conversation participant, update notification token timestamps,
        send auth_ok, and replay any missed messages. Returns False if access is denied.
        """
        async with self.session_factory() as session:
            repos = Repositories.from_session(session)

            if not await self._check_participant(repos, user_id):
                return False

            await self._touch_notification_tokens(repos, session, user_id)
            await self._send(WsAuthOkMessage(conversation_id=self.conversation_id))
            await self._replay_missed_messages(repos)

        self._user_id = user_id
        await self.chat_redis.set_presence(self.conversation_id, user_id)
        return True

    async def _check_participant(self, repos: Repositories, user_id: UUID) -> bool:
        conv = await repos.conversations.get_by_id(self.conversation_id)
        if conv is None or user_id not in (conv.buyer_id, conv.seller_id):
            await self._close_with_error(WsErrorMessage(code="forbidden"), 4003)
            return False

        return True

    async def _touch_notification_tokens(
        self, repos: Repositories, session: AsyncSession, user_id: UUID
    ) -> None:
        notification_tokens = await repos.notification_tokens.get_tokens_for_user(
            user_id
        )
        if notification_tokens:
            for notification_token in notification_tokens:
                await repos.notification_tokens.touch_last_seen(notification_token.id)
            await session.commit()

    async def _replay_missed_messages(self, repos: Repositories) -> None:
        if self.last_message_id is None:
            return
        missed = await repos.messages.get_messages_after(
            self.conversation_id, self.last_message_id
        )
        for msg in missed:
            await self._send(MessageResponse.model_validate(msg))

    async def _run_message_loop(self) -> None:
        channel = ChatRedisManager.conversation_channel(self.conversation_id)
        pubsub = self.chat_redis.pubsub()
        await pubsub.subscribe(channel)

        presence_task = asyncio.create_task(self._refresh_presence())
        forward_task = asyncio.create_task(self._forward_redis_to_ws(pubsub))

        try:
            await self._receive_client_messages()
        finally:
            presence_task.cancel()
            forward_task.cancel()
            await asyncio.gather(presence_task, forward_task, return_exceptions=True)
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()
            await self.chat_redis.delete_presence(self.conversation_id, self._user_id)

    async def _receive_client_messages(self) -> None:
        while True:
            try:
                raw = await self.websocket.receive_text()
                msg = json.loads(raw)
                if msg.get("type") == "ping":
                    await self._send(WsPongMessage())
                elif msg.get("type") == "typing":
                    await self.chat_redis.publish_typing(
                        self.conversation_id, self._user_id
                    )
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                logger.warning(
                    "Malformed WS message in conversation %s", self.conversation_id
                )
                # Keep the connection alive, just skip the bad frame

    async def _refresh_presence(self) -> None:
        while True:
            await asyncio.sleep(PRESENCE_TTL // 2)
            await self.chat_redis.refresh_presence(self.conversation_id, self._user_id)

    async def _forward_redis_to_ws(self, pubsub) -> None:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue

            data = message["data"]
            if isinstance(data, bytes):
                data = data.decode()

            await self.websocket.send_text(data)

    async def _send(self, msg: BaseModel) -> None:
        await self.websocket.send_text(msg.model_dump_json())

    async def _close_with_error(self, msg: WsErrorMessage, close_code: int) -> None:
        await self._send(msg)
        await self.websocket.close(code=close_code)
