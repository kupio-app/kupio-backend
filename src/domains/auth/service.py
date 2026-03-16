from fastapi import HTTPException, status

from src.core.config import get_config
from src.core.database.repositories import Repositories
from src.core.database.uow import UoW
from src.core.security import (
    create_access_token,
    generate_refresh_token,
    verify_password,
    hash_refresh_token,
)
from src.domains.users.models import User
from src.domains.users.service import UsersService
from src.domains.users.repository import UsersRepository

from .repository import SessionsRepository
from .schemas import LoginRequest, RegisterRequest, TokensResponse


class AuthService:
    def __init__(self, repos: Repositories, uow: UoW) -> None:
        self.repos = repos
        self.users_repo: UsersRepository = repos.users
        self.sessions: SessionsRepository = repos.sessions
        self.uow = uow
        self.config = get_config().auth

    async def login(self, payload: LoginRequest) -> TokensResponse:
        user = await self.users_repo.get_by_email(payload.email)
        if user is None or not verify_password(payload.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        async with self.uow:
            return await self._issue_token_pair(user)

    async def refresh(self, refresh_token: str) -> TokensResponse:
        refresh_hash = hash_refresh_token(refresh_token)
        active_session = await self.sessions.get_active_by_token_hash(refresh_hash)
        if active_session is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )

        user = await self.users_repo.get_by_id(active_session.user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        async with self.uow:
            await self.sessions.revoke_by_id(active_session.id)
            return await self._issue_token_pair(user)

    async def logout(self, refresh_token: str) -> None:
        refresh_hash = hash_refresh_token(refresh_token)
        async with self.uow:
            await self.sessions.revoke_by_token_hash(refresh_hash)

    async def register(self, payload: RegisterRequest) -> TokensResponse:
        users_service = UsersService(self.repos, self.uow)

        user = await users_service.create_user(
            password=payload.password, email=payload.email, username=payload.username
        )

        async with self.uow:
            return await self._issue_token_pair(user)

    async def _issue_token_pair(self, user: User) -> TokensResponse:
        access_token, _ = create_access_token(
            user_id=str(user.id),
            config=self.config,
        )
        refresh_token, expire_at = generate_refresh_token(self.config)

        await self.sessions.create_session(
            user_id=user.id,
            token_hash=hash_refresh_token(refresh_token),
            device_id="unknown",
            expires_at=expire_at,
        )

        return TokensResponse(access_token=access_token, refresh_token=refresh_token)
