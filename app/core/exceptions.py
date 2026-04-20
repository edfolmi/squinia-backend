"""
Application-level exceptions with machine-readable error codes.

Services raise ``AppError``; the global handler in ``error_handler.py``
converts it into the standard API envelope automatically.
"""
from __future__ import annotations


class AppError(Exception):
    """
    Structured application error.

    Attributes:
        status_code: HTTP status code to return.
        code: Machine-readable error code (e.g. ``USER_NOT_FOUND``).
        message: Human-readable description.
        headers: Optional HTTP headers (e.g. ``WWW-Authenticate``).
    """

    def __init__(
        self,
        *,
        status_code: int = 400,
        code: str = "BAD_REQUEST",
        message: str = "Something went wrong",
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.headers = headers
        super().__init__(message)
