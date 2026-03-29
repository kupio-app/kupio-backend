import datetime
import uuid

from sqlalchemy import select, update

from src.core.database.base_repository import BaseRepository

from .models import OAuthIdentity, Session


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

    async def get_active_by_token_and_device(
        self, token_hash: str, device_id: str
    ) -> Session | None:
        return await self._get(
            Session,
            Session.token_hash == token_hash,
            Session.device_id == device_id,
            Session.is_revoked.is_(False),
            Session.expires_at > datetime.datetime.now(datetime.UTC),
        )

    async def list_active_by_user_id(self, user_id: uuid.UUID) -> list[Session]:
        stmt = (
            select(Session)
            .where(
                Session.user_id == user_id,
                Session.is_revoked.is_(False),
                Session.expires_at > datetime.datetime.now(datetime.UTC),
            )
            .order_by(Session.last_used_at.desc())
        )
        return list(await self.session.scalars(stmt))

    async def revoke_by_id(self, session_id: uuid.UUID) -> bool:
        updated = await self._update(
            Session,
            [Session.id == session_id, Session.is_revoked.is_(False)],
            is_revoked=True,
            last_used_at=datetime.datetime.now(datetime.UTC),
        )
        return updated is not None

    async def revoke_by_id_and_user_id(
        self, session_id: uuid.UUID, user_id: uuid.UUID
    ) -> bool:
        query = (
            update(Session)
            .where(
                Session.id == session_id,
                Session.user_id == user_id,
                Session.is_revoked.is_(False),
            )
            .values(
                is_revoked=True,
                last_used_at=datetime.datetime.now(datetime.UTC),
            )
        )
        result = await self.session.execute(query)
        await self.session.flush()
        return bool(getattr(result, "rowcount", 0) > 0)

    async def revoke_all_by_user_id(self, user_id: uuid.UUID) -> int:
        query = (
            update(Session)
            .where(Session.user_id == user_id, Session.is_revoked.is_(False))
            .values(
                is_revoked=True,
                last_used_at=datetime.datetime.now(datetime.UTC),
            )
        )
        result = await self.session.execute(query)
        await self.session.flush()
        return int(getattr(result, "rowcount", 0) or 0)

    async def revoke_active_for_device(
        self, user_id: uuid.UUID, device_id: str
    ) -> None:
        await self._update(
            Session,
            [
                Session.user_id == user_id,
                Session.device_id == device_id,
                Session.is_revoked == False,
                Session.expires_at > datetime.datetime.now(datetime.UTC),
            ],
            is_revoked=True,
        )

    async def revoke_by_token_hash(self, token_hash: str) -> bool:
        session = await self._get(Session, Session.token_hash == token_hash)
        if session is None or session.is_revoked:
            return False

        return await self.revoke_by_id(session.id)


class OAuthIdentitiesRepository(BaseRepository):
    async def create_identity(
        self,
        *,
        user_id: uuid.UUID,
        provider: str,
        provider_sub: str,
    ) -> OAuthIdentity:
        return await self._add(
            OAuthIdentity,
            user_id=user_id,
            provider=provider,
            provider_sub=provider_sub,
            last_login_at=datetime.datetime.now(datetime.UTC),
        )

    async def get_by_provider_sub(
        self,
        *,
        provider: str,
        provider_sub: str,
    ) -> OAuthIdentity | None:
        return await self._get(
            OAuthIdentity,
            OAuthIdentity.provider == provider,
            OAuthIdentity.provider_sub == provider_sub,
        )

    async def touch_last_login(self, identity_id: uuid.UUID) -> None:
        await self._update(
            OAuthIdentity,
            [OAuthIdentity.id == identity_id],
            load_result=False,
            last_login_at=datetime.datetime.now(datetime.UTC),
        )
