"""
Global exception handlers — every error returns the standard API envelope.
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.exceptions import AppError
from app.core.logging import get_logger
from app.schemas.response import ErrorDetail, fail

logger = get_logger(__name__)


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Handle structured ``AppError`` raised by services / dependencies."""
    logger.warning(
        "App error",
        path=request.url.path,
        code=exc.code,
        message=exc.message,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=fail(code=exc.code, message=exc.message),
        headers=exc.headers,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError,
) -> JSONResponse:
    """Pydantic / FastAPI validation errors → 422 envelope."""
    logger.warning("Validation error", path=request.url.path, errors=exc.errors())
    details = [
        ErrorDetail(
            field=".".join(str(loc) for loc in err.get("loc", [])),
            message=err.get("msg", "Invalid value"),
        )
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=fail(
            code="VALIDATION_ERROR",
            message="Invalid request data",
            details=details,
        ),
    )


async def database_exception_handler(
    request: Request, exc: SQLAlchemyError,
) -> JSONResponse:
    """Database errors → 409 (integrity) or 500."""
    logger.error("Database error", path=request.url.path, error=str(exc))
    if isinstance(exc, IntegrityError):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=fail(code="CONFLICT", message="Resource conflict"),
        )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=fail(code="INTERNAL_ERROR", message="Something went wrong"),
    )


async def general_exception_handler(
    request: Request, exc: Exception,
) -> JSONResponse:
    """Catch-all — never leak internals."""
    logger.error(
        "Unexpected error",
        path=request.url.path,
        error=str(exc),
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=fail(code="INTERNAL_ERROR", message="Something went wrong"),
    )
