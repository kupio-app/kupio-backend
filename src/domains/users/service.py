from fastapi import HTTPException

from src.core.database.repositories import Repositories
from src.core.database.uow import UoW
from src.core.security.password import hash_password

from .repository import UsersRepository
from .schemas import UserCreate


class UsersService:
    def __init__(self, repos: Repositories, uow: UoW) -> None:
        self.repos = repos
        self.users_repo: UsersRepository = repos.users
        self.uow = uow

    async def get_user(self, username: str):
        user = await self.users_repo.get_by_username(username)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")

        return user

    async def create_user(self, data: UserCreate):
        async with self.uow:
            existing = await self.users_repo.get_by_email(data.email)
            if existing is not None:
                raise HTTPException(status_code=409, detail="User already exists")

            return await self.users_repo.create(
                email=data.email,
                first_name=data.first_name,
                last_name=data.last_name,
                username=data.username,
                password_hash=hash_password(data.password),
            )
