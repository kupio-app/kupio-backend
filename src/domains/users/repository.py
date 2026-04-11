import uuid
import datetime

from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.core.database.base_repository import BaseRepository

from .enums import UserRole, DevicePlatform
from .models import User, DeviceToken


class UsersRepository(BaseRepository):
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

    async def get_by_phone(self, phone: str) -> User | None:
        return await self._get(User, User.phone == phone)

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self._get(User, User.id == user_id)

    async def get_by_id_str(self, user_id: str) -> User | None:
        try:
            parsed_id = uuid.UUID(user_id)
        except ValueError:
            return None

        return await self._get(User, User.id == parsed_id)

    async def get_by_email(self, email: str) -> User | None:
        return await self._get(User, User.email == email)

    async def update(self, user_id: uuid.UUID, **kwargs) -> User:
        return await self._update(User, [User.id == user_id], **kwargs)

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


class DeviceTokensRepository(BaseRepository):
    async def upsert(
        self, *, user_id: uuid.UUID, token: str, platform: DevicePlatform
    ) -> DeviceToken:
        now = datetime.datetime.now(datetime.UTC)
        stmt = (
            pg_insert(DeviceToken)
            .values(
                user_id=user_id,
                token=token,
                platform=platform,
                last_seen_at=now,
            )
            .on_conflict_do_update(
                constraint="uq_device_token_user_platform_token",
                set_={"last_seen_at": now},
            )
            .returning(DeviceToken)
        )
        result = await self.session.scalar(stmt)
        await self.session.flush()
        return result

    async def touch_last_seen(self, token_id: uuid.UUID) -> None:
        await self._update(
            DeviceToken,
            [DeviceToken.id == token_id],
            load_result=False,
            last_seen_at=datetime.datetime.now(datetime.UTC),
        )

    async def get_tokens_for_user(self, user_id: uuid.UUID) -> list[DeviceToken]:
        return await self._get_many(DeviceToken, DeviceToken.user_id == user_id)

    async def delete_by_id(self, token_id: uuid.UUID) -> None:
        await self._delete(DeviceToken, DeviceToken.id == token_id)
