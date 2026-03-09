from fastapi import APIRouter
from .users.router import router as users_router

api_router = APIRouter()
api_router.include_router(users_router, tags=["Users"], prefix="/users")
