"""Amazon SES transactional email."""
from __future__ import annotations

import asyncio

from app.core.logging import get_logger

logger = get_logger(__name__)


class SesEmailProvider:
    def __init__(self, *, region: str, from_address: str) -> None:
        self._region = region
        self._from = from_address

    async def send(
        self,
        *,
        to_address: str,
        subject: str,
        text_body: str,
        html_body: str | None = None,
    ) -> None:
        try:
            import boto3
        except ImportError as e:
            raise RuntimeError("boto3 is required for SES email delivery") from e

        client = boto3.client("ses", region_name=self._region)
        body: dict = {"Text": {"Charset": "UTF-8", "Data": text_body}}
        if html_body:
            body["Html"] = {"Charset": "UTF-8", "Data": html_body}

        def _send() -> None:
            client.send_email(
                Source=self._from,
                Destination={"ToAddresses": [to_address]},
                Message={
                    "Subject": {"Charset": "UTF-8", "Data": subject},
                    "Body": body,
                },
            )

        await asyncio.to_thread(_send)
        logger.info("email_ses_sent", to=to_address, subject=subject)
