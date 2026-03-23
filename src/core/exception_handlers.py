from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .exceptions import DomainError


async def handle_domain_error(_: Request, exc: Exception) -> JSONResponse:
    domain_error = exc
    if not isinstance(domain_error, DomainError):
        domain_error = DomainError()

    return JSONResponse(
        status_code=domain_error.status_code,
        content={"detail": domain_error.detail},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, handle_domain_error)
