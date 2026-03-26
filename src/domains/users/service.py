from src.core.database.repositories import Repositories
from src.core.database.uow import UoW
from .exceptions import UserNotFoundError, UserPhoneConflictError
from .models import User

from .repository import UsersRepository
from .schemas import UpdateUserProfile


class UsersService:
    def __init__(self, repos: Repositories, uow: UoW) -> None:
        self.repos = repos
        self.users_repo: UsersRepository = repos.users
        self.uow = uow

    async def get_user(self, username: str) -> User:
        user = await self.users_repo.get_by_username(username)
        if user is None:
            raise UserNotFoundError()

        return user

    async def update_profile(
        self, current_user: User, user_data: UpdateUserProfile
    ) -> (
        User
    ):  # Here response cant be None, because we are updating existing current user
        if user_data.phone is not None:
            user = await self.users_repo.get_by_phone(user_data.phone)
            if user is not None and user.id != current_user.id:
                raise UserPhoneConflictError()

        async with self.uow:
            return await self.users_repo.update(
                user_id=current_user.id, **user_data.model_dump(exclude_unset=True)
            )
