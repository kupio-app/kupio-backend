import uuid

from src.core.database.base_repository import BaseRepository
from .enums import UserRole

from .models import User


class UsersRepository(BaseRepository):
    async def create(
        self,
        *,
        email: str,
        username: str,
        password_hash: str,
        role: UserRole = UserRole.USER,
    ) -> User:
        return await self._add(
            User,
            email=email,
            username=username,
            password_hash=password_hash,
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
