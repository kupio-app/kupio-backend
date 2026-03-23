import uuid

from fastapi import APIRouter, Depends, status, Body

from src.core.database.uow import UoW
from src.core.dependencies import get_current_user, get_uow, RepositoriesDeps
from src.domains.users.models import User
from src.domains.users.schemas import UserPrivate

from .schemas import (
    LoginRequest,
    MeResponse,
    RefreshRequest,
    RegisterRequest,
    TokensResponse,
    SessionsResponse,
    ChangePasswordRequest,
)
from .service import AuthService

router = APIRouter()


def get_auth_service(
    repos: RepositoriesDeps,
    uow: UoW = Depends(get_uow),
) -> AuthService:
    return AuthService(repos=repos, uow=uow)


@router.post("/login", response_model=TokensResponse)
async def login(
    payload: LoginRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokensResponse:
    return await service.login(payload)


@router.post("/refresh", response_model=TokensResponse)
async def refresh(
    payload: RefreshRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokensResponse:
    return await service.refresh(payload)


@router.post("/logout", status_code=status.HTTP_202_ACCEPTED)
async def logout(
    refresh_token: str = Body(..., embed=True),
    service: AuthService = Depends(get_auth_service),
) -> None:
    await service.logout(refresh_token)


@router.get("/me", response_model=MeResponse)
async def me(current_user: User = Depends(get_current_user)) -> MeResponse:
    return MeResponse(user=UserPrivate.model_validate(current_user))


@router.get("/sessions", response_model=SessionsResponse)
async def list_sessions(
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
) -> SessionsResponse:
    return await service.list_sessions(current_user)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
) -> None:
    await service.revoke_session(current_user=current_user, session_id=session_id)


@router.delete("/sessions", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_all_sessions(
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
) -> None:
    await service.revoke_all_sessions(current_user)


@router.post("/change-password", response_model=TokensResponse)
async def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
) -> TokensResponse:
    return await service.change_password(current_user=current_user, payload=payload)


# TODO: /forgot-password , /reset-password


@router.post(
    "/register",
    response_model=TokensResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    payload: RegisterRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokensResponse:
    return await service.register(payload)
