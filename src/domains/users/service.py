from fastapi import HTTPException

from src.core.database.repositories import Repositories
from src.core.database.uow import UoW

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
