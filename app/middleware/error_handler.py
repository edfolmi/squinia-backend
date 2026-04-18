"""
Global error handling middleware.
Provides consistent error responses and logging.
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.core.logging import get_logger

logger = get_logger(__name__)


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle Pydantic validation errors with detailed error messages.
    """
    logger.warning(
        "Validation error",
        path=request.url.path,
        errors=exc.errors()
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": exc.errors(),
            "message": "Validation error"
        }
    )


async def database_exception_handler(request: Request, exc: SQLAlchemyError):
    """
    Handle database errors gracefully.
    """
    logger.error(
        "Database error",
        path=request.url.path,
        error=str(exc)
    )
    
    if isinstance(exc, IntegrityError):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "detail": "Database integrity constraint violation",
                "message": "Resource conflict"
            }
        )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Database error occurred",
            "message": "Internal server error"
        }
    )


async def general_exception_handler(request: Request, exc: Exception):
    """
    Catch-all exception handler for unexpected errors.
    """
    logger.error(
        "Unexpected error",
        path=request.url.path,
        error=str(exc),
        exc_info=True
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An unexpected error occurred",
            "message": "Internal server error"
        }
    )
