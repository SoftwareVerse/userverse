"""Services used by background job handlers."""

from __future__ import annotations

import asyncio
from functools import partial

from app.utils.email.sender import deliver_email


class EmailService:
    """Provide async wrappers around synchronous email delivery."""

    async def send_async(
        self,
        to: str,
        subject: str,
        html_body: str,
        *,
        reason: str = "job",
    ) -> None:
        await asyncio.to_thread(
            partial(deliver_email, to, subject, html_body, reason=reason)
        )
