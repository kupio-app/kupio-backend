import uuid

from fastapi import HTTPException, status

from src.core.config import get_config
from src.core.database.repositories import Repositories
from src.core.database.uow import UoW
from src.core.security import (
    create_access_token,
    generate_refresh_token,
    verify_password,
    hash_refresh_token,
    hash_password,
)
from src.domains.users.models import User
from src.domains.users.repository import UsersRepository

from .repository import SessionsRepository
from .schemas import (
    LoginRequest,
    RegisterRequest,
    TokensResponse,
    RefreshRequest,
    SessionsResponse,
    SessionInfo,
    ChangePasswordRequest,
)


class AuthService:
    def __init__(self, repos: Repositories, uow: UoW) -> None:
        self.repos = repos
        self.users_repo: UsersRepository = repos.users
        self.sessions: SessionsRepository = repos.sessions
        self.uow = uow
        self.config = get_config().auth

    async def login(self, payload: LoginRequest) -> TokensResponse:
        user = await self.users_repo.get_by_email(str(payload.email))
        if user is None or not verify_password(payload.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        async with self.uow:
            # Revoke existing session for the same device to prevent multiple active sessions on the same device
            # Don't show error if there is active session, just revoke it and issue new tokens
            await self.sessions.revoke_active_for_device(
                user_id=user.id, device_id=payload.device_id
            )

            return await self._issue_token_pair(user, device_id=payload.device_id)

    async def refresh(self, payload: RefreshRequest) -> TokensResponse:
        refresh_hash = hash_refresh_token(payload.refresh_token)
        active_session = await self.sessions.get_active_by_token_and_device(
            token_hash=refresh_hash,
            device_id=payload.device_id,
        )
        if active_session is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )

        user = await self.users_repo.get_by_id(active_session.user_id)
        async with self.uow:
            await self.sessions.revoke_by_id(active_session.id)
            return await self._issue_token_pair(
                user, device_id=active_session.device_id
            )

    async def logout(self, refresh_token: str) -> None:
        refresh_hash = hash_refresh_token(refresh_token)
        async with self.uow:
            await self.sessions.revoke_by_token_hash(refresh_hash)

    async def register(self, payload: RegisterRequest) -> TokensResponse:
        async with self.uow:
            user_by_email = await self.users_repo.get_by_email(str(payload.email))
            if user_by_email is not None:
                raise HTTPException(status_code=409, detail="Email already taken")

            user_by_username = await self.users_repo.get_by_username(payload.username)
            if user_by_username is not None:
                raise HTTPException(status_code=409, detail="Username already taken")

            user = await self.users_repo.create(
                email=str(payload.email),
                username=payload.username,
                password_hash=hash_password(payload.password),
            )

            return await self._issue_token_pair(user, device_id=payload.device_id)

    async def list_sessions(self, current_user: User) -> SessionsResponse:
        sessions = await self.sessions.list_active_by_user_id(current_user.id)
        return SessionsResponse(
            sessions=[SessionInfo.model_validate(session) for session in sessions]
        )

    async def revoke_session(self, current_user: User, session_id: uuid.UUID) -> None:
        async with self.uow:
            revoked = await self.sessions.revoke_by_id_and_user_id(
                session_id=session_id,
                user_id=current_user.id,
            )
            if not revoked:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Session not found",
                )

    async def revoke_all_sessions(self, current_user: User) -> None:
        async with self.uow:
            await self.sessions.revoke_all_by_user_id(current_user.id)

    async def change_password(
        self, current_user: User, payload: ChangePasswordRequest
    ) -> TokensResponse:
        if payload.current_password == payload.new_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be different from current password",
            )

        async with self.uow:
            if not verify_password(
                payload.current_password, current_user.password_hash
            ):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid current password",
                )

            user = await self.users_repo.update(
                user_id=current_user.id,
                password_hash=hash_password(payload.new_password),
            )
            await self.sessions.revoke_all_by_user_id(current_user.id)

            return await self._issue_token_pair(user, device_id=payload.device_id)

    async def _issue_token_pair(self, user: User, *, device_id: str) -> TokensResponse:
        access_token, _, access_expires_at = create_access_token(
            user_id=str(user.id),
            config=self.config,
        )
        refresh_token, refresh_expires_at = generate_refresh_token(self.config)

        await self.sessions.create_session(
            user_id=user.id,
            token_hash=hash_refresh_token(refresh_token),
            device_id=device_id,
            expires_at=refresh_expires_at,
        )

        return TokensResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            access_expires_at=access_expires_at,
            refresh_expires_at=int(refresh_expires_at.timestamp()),
        )
