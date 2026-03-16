import datetime
import uuid

from src.core.database.base_repository import BaseRepository

from .models import Session


class SessionsRepository(BaseRepository):
    async def create_session(
        self,
        user_id: uuid.UUID,
        token_hash: str,
        device_id: str,
        expires_at: datetime.datetime,
    ) -> Session:
        return await self._add(
            Session,
            user_id=user_id,
            token_hash=token_hash,
            device_id=device_id,
            expires_at=expires_at,
            last_used_at=datetime.datetime.now(datetime.UTC),
            is_revoked=False,
        )

    async def get_active_by_token_hash(self, token_hash: str) -> Session | None:
        return await self._get(
            Session,
            Session.token_hash == token_hash,
            Session.is_revoked.is_(False),
            Session.expires_at > datetime.datetime.now(datetime.UTC),
        )

    async def revoke_by_id(self, session_id: uuid.UUID) -> bool:
        updated = await self._update(
            Session,
            [Session.id == session_id, Session.is_revoked.is_(False)],
            is_revoked=True,
            last_used_at=datetime.datetime.now(datetime.UTC),
        )
        return updated is not None

    async def revoke_by_token_hash(self, token_hash: str) -> bool:
        session = await self._get(Session, Session.token_hash == token_hash)
        if session is None or session.is_revoked:
            return False

        return await self.revoke_by_id(session.id)
