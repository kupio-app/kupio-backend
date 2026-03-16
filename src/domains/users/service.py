from fastapi import HTTPException

from src.core.database.repositories import Repositories
from src.core.database.uow import UoW
from src.core.security.password import hash_password

from .repository import UsersRepository


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

    async def create_user(self, email: str, username: str, password: str):
        async with self.uow:
            user_by_email = await self.users_repo.get_by_email(email)
            if user_by_email is not None:
                raise HTTPException(status_code=400, detail="User already exists")

            user_by_username = await self.users_repo.get_by_username(username)
            if user_by_username is not None:
                raise HTTPException(status_code=400, detail="User already exists")

            return await self.users_repo.create(
                email=email,
                username=username,
                password_hash=hash_password(password),
            )
