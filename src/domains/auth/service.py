import uuid

from src.core.config import get_config
from src.core.database.repositories import Repositories
from src.core.database.uow import UoW
from src.core.security import (
    GoogleIdTokenClaims,
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_google_id_token,
    verify_password,
)
from src.domains.users.models import User
from src.domains.users.repository import UsersRepository

from .exceptions import (
    EmailAlreadyTakenError,
    InvalidCredentialsError,
    InvalidGoogleTokenError,
    InvalidCurrentPasswordError,
    InvalidRefreshTokenError,
    NewPasswordMustDifferError,
    PasswordAlreadySetError,
    SessionNotFoundError,
    UsernameAlreadyTakenError,
)
from .repository import OAuthIdentitiesRepository, SessionsRepository
from .schemas import (
    GoogleLoginRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    ChangePasswordRequest,
    SessionInfo,
    SessionsResponse,
    SetPasswordRequest,
    TokensResponse,
)

_GOOGLE_PROVIDER = "google"


class AuthService:
    def __init__(self, repos: Repositories, uow: UoW) -> None:
        self.repos = repos
        self.users_repo: UsersRepository = repos.users
        self.sessions: SessionsRepository = repos.sessions
        self.oauth_identities: OAuthIdentitiesRepository = repos.oauth_identities
        self.uow = uow
        self.config = get_config().auth

    async def login(self, payload: LoginRequest) -> TokensResponse:
        user = await self.users_repo.get_by_email(str(payload.email))
        if (
            user is None
            or user.password_hash is None
            or not verify_password(payload.password, user.password_hash)
        ):
            raise InvalidCredentialsError()

        async with self.uow:
            # Revoke existing session for the same device to prevent multiple active sessions on the same device
            # Don't show error if there is active session, just revoke it and issue new tokens
            await self.sessions.revoke_active_for_device(
                user_id=user.id, device_id=payload.device_id
            )

            return await self._issue_token_pair(user, device_id=payload.device_id)

    async def google_login(self, payload: GoogleLoginRequest) -> TokensResponse:
        claims = await verify_google_id_token(
            payload.id_token,
            client_ids=self.config.google_client_ids,
        )
        if not claims["email_verified"]:
            raise InvalidGoogleTokenError("Google email must be verified")

        async with self.uow:
            user = await self._resolve_google_user(claims)
            await self.sessions.revoke_active_for_device(
                user_id=user.id,
                device_id=payload.device_id,
            )
            return await self._issue_token_pair(
                user,
                device_id=payload.device_id,
                needs_username=user.needs_username,
            )

    async def refresh(self, payload: RefreshRequest) -> TokensResponse:
        refresh_hash = hash_refresh_token(payload.refresh_token)
        active_session = await self.sessions.get_active_by_token_and_device(
            token_hash=refresh_hash,
            device_id=payload.device_id,
        )
        if active_session is None:
            raise InvalidRefreshTokenError()

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
                raise EmailAlreadyTakenError()

            user_by_username = await self.users_repo.get_by_username(payload.username)
            if user_by_username is not None:
                raise UsernameAlreadyTakenError()

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
                raise SessionNotFoundError()

    async def revoke_all_sessions(self, current_user: User) -> None:
        async with self.uow:
            await self.sessions.revoke_all_by_user_id(current_user.id)

    async def change_password(
        self, current_user: User, payload: ChangePasswordRequest
    ) -> TokensResponse:
        if payload.current_password == payload.new_password:
            raise NewPasswordMustDifferError()
        if current_user.password_hash is None:
            raise InvalidCurrentPasswordError()

        async with self.uow:
            if not verify_password(
                payload.current_password, current_user.password_hash
            ):
                raise InvalidCurrentPasswordError()

            user = await self.users_repo.update(
                user_id=current_user.id,
                password_hash=hash_password(payload.new_password),
            )
            await self.sessions.revoke_all_by_user_id(current_user.id)

            return await self._issue_token_pair(user, device_id=payload.device_id)

    async def set_password(
        self, current_user: User, payload: SetPasswordRequest
    ) -> TokensResponse:
        if current_user.password_hash is not None:
            raise PasswordAlreadySetError()

        async with self.uow:
            user = await self.users_repo.update(
                user_id=current_user.id,
                password_hash=hash_password(payload.new_password),
            )
            await self.sessions.revoke_all_by_user_id(current_user.id)
            return await self._issue_token_pair(user, device_id=payload.device_id)

    async def _resolve_google_user(self, claims: GoogleIdTokenClaims) -> User:
        identity = await self.oauth_identities.get_by_provider_sub(
            provider=_GOOGLE_PROVIDER,
            provider_sub=claims["sub"],
        )
        if identity is not None:
            user = await self.users_repo.get_by_id(identity.user_id)
            if user is None:
                raise InvalidGoogleTokenError()
            await self.oauth_identities.touch_last_login(identity.id)
            return user

        user = await self.users_repo.get_by_email(claims["email"])
        if user is None:
            user = await self.users_repo.create(
                email=claims["email"],
                username=None,
                password_hash=None,
                first_name=claims.get("given_name"),
                last_name=claims.get("family_name"),
            )

        await self.oauth_identities.create_identity(
            user_id=user.id,
            provider=_GOOGLE_PROVIDER,
            provider_sub=claims["sub"],
        )

        return user

    async def _issue_token_pair(
        self,
        user: User,
        *,
        device_id: str,
        needs_username: bool | None = None,
    ) -> TokensResponse:
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
            needs_username=(
                user.needs_username if needs_username is None else needs_username
            ),
        )
