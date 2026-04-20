"""Authenticate internal worker endpoints."""
from typing import Annotated

from fastapi import Header

from app.core.config import settings
from app.core.exceptions import AppError


async def verify_internal_api_key(
    x_internal_key: Annotated[str | None, Header(alias="X-Internal-Key")] = None,
) -> None:
    if not x_internal_key or x_internal_key != settings.INTERNAL_API_KEY:
        raise AppError(status_code=401, code="UNAUTHORIZED", message="Invalid internal API key")
