from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

from app.shared.domain.exceptions import DomainException, EntityNotFound, InvalidStateTransition

_STATUS_MAP = {
    "NOT_FOUND": 404,
    "INVALID_TRANSITION": 409,
    "CONFLICT": 409,
    "FORBIDDEN": 403,
    "INFRASTRUCTURE_ERROR": 503,
}


async def domain_exception_handler(request: Request, exc: DomainException) -> JSONResponse:
    status_code = _STATUS_MAP.get(exc.code, 400)
    return JSONResponse(
        status_code=status_code,
        content={"error": exc.code, "message": exc.message},
    )
