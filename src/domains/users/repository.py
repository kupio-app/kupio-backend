import uuid
import datetime

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import selectinload

from src.core.database.base_repository import BaseRepository

from .enums import UserRole, DevicePlatform
from .models import User, NotificationToken, Moderator


class UsersRepository(BaseRepository):
    @staticmethod
    def _response_read_options():
        return (selectinload(User.avatar_image),)

    async def create(
        self,
        *,
        email: str,
        username: str | None,
        password_hash: str | None,
        first_name: str | None = None,
        last_name: str | None = None,
        role: UserRole = UserRole.USER,
    ) -> User:
        return await self._add(
            User,
            email=email,
            username=username,
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name,
            role=role,
        )

    async def get_by_username(self, username: str) -> User | None:
        return await self._get(User, User.username == username)

    async def get_for_response_by_username(self, username: str) -> User | None:
        return await self._get(
            User,
            User.username == username,
            options=self._response_read_options(),
        )

    async def get_by_phone(self, phone: str) -> User | None:
        return await self._get(User, User.phone == phone)

    async def get_by_id(
        self, user_id: uuid.UUID, *, populate_existing: bool = False
    ) -> User | None:
        return await self._get(
            User,
            User.id == user_id,
            populate_existing=populate_existing,
        )

    async def get_for_response_by_id(
        self, user_id: uuid.UUID, *, populate_existing: bool = False
    ) -> User | None:
        return await self._get(
            User,
            User.id == user_id,
            options=self._response_read_options(),
            populate_existing=populate_existing,
        )

    async def get_by_id_str(self, user_id: str) -> User | None:
        try:
            parsed_id = uuid.UUID(user_id)
        except ValueError:
            return None

        return await self._get(User, User.id == parsed_id)

    async def get_by_email(self, email: str) -> User | None:
        return await self._get(User, User.email == email)

    async def update(self, user_id: uuid.UUID, **kwargs) -> User:
        await self._update(User, [User.id == user_id], load_result=False, **kwargs)
        return await self.get_for_response_by_id(user_id, populate_existing=True)

    async def deduct_balance(self, user_id: uuid.UUID, amount: int) -> bool:
        result = await self._update(
            User,
            [User.id == user_id, User.balance >= amount],
            balance=User.balance - amount,
            load_result=True,
        )
        return result is not None

    async def add_balance(self, user_id: uuid.UUID, amount: int) -> None:
        await self._update(
            User,
            [User.id == user_id],
            load_result=False,
            balance=User.balance + amount,
        )

    async def soft_delete_by_id(self, user_id: uuid.UUID) -> bool:
        return await self._soft_delete(User, User.id == user_id)


class NotificationTokensRepository(BaseRepository):
    async def upsert(
        self,
        *,
        user_id: uuid.UUID,
        token: str,
        platform: DevicePlatform,
        device_id: str | None = None,
    ) -> NotificationToken:
        now = datetime.datetime.now(datetime.UTC)
        stmt = (
            pg_insert(NotificationToken)
            .values(
                user_id=user_id,
                token=token,
                platform=platform,
                device_id=device_id,
                last_seen_at=now,
            )
            .on_conflict_do_update(
                constraint="uq_notification_token_user_platform_token",
                set_={"device_id": device_id, "last_seen_at": now},
            )
            .returning(NotificationToken)
        )
        result = await self.session.scalar(stmt)
        await self.session.flush()
        return result

    async def touch_last_seen(self, token_id: uuid.UUID) -> None:
        await self._update(
            NotificationToken,
            [NotificationToken.id == token_id],
            load_result=False,
            last_seen_at=datetime.datetime.now(datetime.UTC),
        )

    async def get_tokens_for_user(self, user_id: uuid.UUID) -> list[NotificationToken]:
        return await self._get_many(
            NotificationToken, NotificationToken.user_id == user_id
        )

    async def delete_by_id(self, token_id: uuid.UUID) -> None:
        await self._delete(NotificationToken, NotificationToken.id == token_id)

    async def delete_by_user_and_device(
        self, *, user_id: uuid.UUID, device_id: str
    ) -> None:
        await self._delete(
            NotificationToken,
            NotificationToken.user_id == user_id,
            NotificationToken.device_id == device_id,
        )


class ModeratorsRepository(BaseRepository):
    async def create(self, *, user_id: uuid.UUID) -> Moderator:
        return await self._add(Moderator, user_id=user_id)

    async def get_by_id(self, moderator_id: uuid.UUID) -> Moderator | None:
        return await self._get(Moderator, Moderator.id == moderator_id)

    async def get_by_user_id(self, user_id: uuid.UUID) -> Moderator | None:
        return await self._get(Moderator, Moderator.user_id == user_id)

    async def touch_last_action(
        self,
        moderator_id: uuid.UUID,
        *,
        at: datetime.datetime,
    ) -> Moderator | None:
        return await self._update(
            Moderator,
            [Moderator.id == moderator_id],
            last_action_at=at,
        )
