"""Construct the configured email provider."""
from __future__ import annotations

from app.core.config import settings
from app.integrations.email.base import ConsoleEmailProvider, EmailProvider, NullEmailProvider
from app.integrations.email.ses import SesEmailProvider


def get_email_provider() -> EmailProvider:
    p = settings.EMAIL_PROVIDER.lower()
    if p == "ses":
        return SesEmailProvider(
            region=settings.AWS_REGION,
            from_address=settings.SES_FROM_EMAIL,
        )
    if p == "console":
        return ConsoleEmailProvider()
    if p in ("none", "null", "disabled"):
        return NullEmailProvider()
    raise ValueError(f"Unknown EMAIL_PROVIDER: {settings.EMAIL_PROVIDER}")
