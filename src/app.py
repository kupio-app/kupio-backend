from fastapi import FastAPI

from .domains.router import api_router
from .lifetime import lifespan
from .core.config import get_config


def get_app() -> FastAPI:
    """
    Get FastAPI application.

    This is the main constructor of an application.

    :return: application.
    """

    config = get_config()

    app = FastAPI(
        title="Kupio Backend",
        docs_url="/api/docs" if not config.debug else None,
        redoc_url="/api/redoc" if not config.debug else None,
        openapi_url="/api/openapi.json" if not config.debug else None,
        lifespan=lifespan,
    )
    app.include_router(api_router, prefix="/api")
    return app
