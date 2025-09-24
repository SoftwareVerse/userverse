"""Background job handlers."""

from __future__ import annotations

import logging
from typing import Any, Dict

from .bus import Job, JobType
from . import composer
from .models import EmailJob
from .services import EmailService

logger = logging.getLogger(__name__)

email_service = EmailService()


async def handle_email(job: Job) -> Dict[str, Any]:
    """Send an email using the job payload."""

    payload = EmailJob.model_validate(job.payload)
    subject, body = composer.render_email(payload.reason, payload.context)
    await email_service.send_async(payload.to, subject, body, reason=payload.reason)
    logger.debug("Email job processed", extra={"email_to": payload.to, "reason": payload.reason})
    return {"email": {"to": payload.to, "subject": subject}, "reason": payload.reason}


HANDLER_MAP = {JobType.EMAIL_SEND: handle_email}
