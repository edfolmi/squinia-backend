"""
Standardised API response envelope.

Every HTTP response follows:
    { "success": bool, "data": T | null, "error": ErrorBody | null, "meta": Meta | null }
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Generic, Optional, TypeVar
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    """Single field-level validation error."""

    field: str
    message: str


class ErrorBody(BaseModel):
    """Machine-readable error payload."""

    code: str
    message: str
    details: list[ErrorDetail] = Field(default_factory=list)


class PaginationMeta(BaseModel):
    """Offset-based pagination metadata."""

    total: int
    limit: int
    offset: int
    has_next: bool


class ResponseMeta(BaseModel):
    """Request-scoped metadata attached to every response."""

    request_id: str = Field(default_factory=lambda: f"req_{uuid4().hex[:12]}")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    pagination: Optional[PaginationMeta] = None


class ApiResponse(BaseModel, Generic[T]):
    """Top-level response envelope for all endpoints."""

    success: bool
    data: Optional[T] = None
    error: Optional[ErrorBody] = None
    meta: ResponseMeta = Field(default_factory=ResponseMeta)

    model_config = ConfigDict(from_attributes=True)


def ok(data: Any, *, meta: Optional[ResponseMeta] = None) -> dict:
    """Build a success envelope dict (use as ``return ok(...)`` in routes)."""
    return ApiResponse(
        success=True,
        data=data,
        error=None,
        meta=meta or ResponseMeta(),
    ).model_dump(mode="json")


def ok_paginated(
    items: Any,
    *,
    total: int,
    page: int,
    page_size: int,
) -> dict:
    """Build a success envelope with pagination in ``meta``."""
    offset = (page - 1) * page_size
    meta = ResponseMeta(
        pagination=PaginationMeta(
            total=total,
            limit=page_size,
            offset=offset,
            has_next=(offset + page_size) < total,
        ),
    )
    return ApiResponse(
        success=True,
        data={"items": items},
        error=None,
        meta=meta,
    ).model_dump(mode="json")


def fail(
    code: str,
    message: str,
    *,
    details: list[ErrorDetail] | None = None,
    request_id: str | None = None,
) -> dict:
    """Build an error envelope dict (used by exception handlers)."""
    meta = ResponseMeta()
    if request_id:
        meta.request_id = request_id
    return ApiResponse(
        success=False,
        data=None,
        error=ErrorBody(code=code, message=message, details=details or []),
        meta=meta,
    ).model_dump(mode="json")
