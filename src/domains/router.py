from fastapi import APIRouter

from .auth.router import router as auth_router
from .users.router import router as users_router

api_router = APIRouter()
api_router.include_router(users_router, tags=["Users"], prefix="/users")
api_router.include_router(auth_router, tags=["Auth"], prefix="/auth")
