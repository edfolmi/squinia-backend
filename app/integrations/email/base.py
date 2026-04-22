"""Email delivery abstraction (SES primary; swappable providers)."""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class EmailProvider(Protocol):
    async def send(
        self,
        *,
        to_address: str,
        subject: str,
        text_body: str,
        html_body: str | None = None,
    ) -> None:
        """Send one transactional message."""
        ...


class NullEmailProvider:
    """No-op (tests or when email is intentionally disabled)."""

    async def send(
        self,
        *,
        to_address: str,
        subject: str,
        text_body: str,
        html_body: str | None = None,
    ) -> None:
        return


class ConsoleEmailProvider:
    """Log-only provider for local development."""

    async def send(
        self,
        *,
        to_address: str,
        subject: str,
        text_body: str,
        html_body: str | None = None,
    ) -> None:
        from app.core.logging import get_logger

        log = get_logger(__name__)
        log.info(
            "email_console_send",
            to=to_address,
            subject=subject,
            text_body=text_body[:2000],
        )
