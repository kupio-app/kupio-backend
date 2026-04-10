from sqlalchemy.exc import IntegrityError

from src.core.database.repositories import Repositories
from src.core.database.uow import UoW
from .exceptions import (
    UserNotFoundError,
    UserPhoneConflictError,
    UserUsernameConflictError,
    UsernameAlreadySetError,
)
from .models import User

from .repository import UsersRepository
from .schemas import SetUsernameRequest, UpdateUserProfile


class UsersService:
    def __init__(self, repos: Repositories, uow: UoW) -> None:
        self.repos = repos
        self.users_repo: UsersRepository = repos.users
        self.uow = uow

    async def get_user(self, username: str) -> User:
        user = await self.users_repo.get_for_response_by_username(username)
        if user is None:
            raise UserNotFoundError()

        return user

    async def get_current_user_for_response(self, user_id) -> User:
        user = await self.users_repo.get_for_response_by_id(user_id)
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

    async def set_username(
        self, current_user: User, payload: SetUsernameRequest
    ) -> User:
        if current_user.username is not None:
            raise UsernameAlreadySetError()

        existing_user = await self.users_repo.get_by_username(payload.username)
        if existing_user is not None and existing_user.id != current_user.id:
            raise UserUsernameConflictError()

        try:
            async with self.uow:
                return await self.users_repo.update(
                    user_id=current_user.id,
                    username=payload.username,
                )
        except IntegrityError:
            raise UserUsernameConflictError()
