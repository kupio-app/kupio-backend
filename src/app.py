from fastapi import FastAPI

from src.core.config import get_config
from src.core.exception_handlers import register_exception_handlers

from .domains.router import api_router
from .lifetime import lifespan


def get_app() -> FastAPI:
    """
    Get FastAPI application.

    This is the main constructor of an application.

    :return: application.
    """

    config = get_config()

    app = FastAPI(
        title="Kupio Backend",
        docs_url="/api/docs" if config.server.debug else None,
        redoc_url="/api/redoc" if config.server.debug else None,
        openapi_url="/api/openapi.json" if config.server.debug else None,
        lifespan=lifespan,
    )

    register_exception_handlers(app)

    app.include_router(api_router, prefix="/api")
    return app
