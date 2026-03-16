from fastapi import APIRouter, Depends, status

from src.core.database.repositories import Repositories
from src.core.database.uow import UoW
from src.core.dependencies import get_current_user, get_repo, get_uow
from src.domains.users.models import User
from src.domains.users.schemas import UserPrivate

from .schemas import (
    LoginRequest,
    MeResponse,
    RefreshRequest,
    RegisterRequest,
    TokensResponse,
)
from .service import AuthService

router = APIRouter()


def get_auth_service(
    repos: Repositories = Depends(get_repo),
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
    return await service.refresh(payload.refresh_token)


@router.post("/logout", status_code=status.HTTP_202_ACCEPTED)
async def logout(
    payload: RefreshRequest,
    service: AuthService = Depends(get_auth_service),
) -> None:
    await service.logout(payload.refresh_token)


@router.get("/me", response_model=MeResponse)
async def me(current_user: User = Depends(get_current_user)) -> MeResponse:
    return MeResponse(user=UserPrivate.model_validate(current_user))


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
