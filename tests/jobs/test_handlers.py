import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))


@pytest.fixture
def anyio_backend():
    return "asyncio"

from app.jobs.bus import Job, JobType
from app.jobs.handlers import handle_email


@pytest.mark.anyio
async def test_handle_email_with_rendered_reason():
    job = Job(
        type=JobType.EMAIL_SEND,
        payload={
            "to": "user@example.com",
            "reason": "rendered",
            "context": {"subject": "Hi", "html_body": "<p>Hello</p>"},
        },
    )

    with patch("app.jobs.handlers.email_service.send_async", new=AsyncMock()) as send_async:
        result = await handle_email(job)

    send_async.assert_awaited_once_with("user@example.com", "Hi", "<p>Hello</p>")
    assert result["reason"] == "rendered"
    assert result["email"]["to"] == "user@example.com"


@pytest.mark.anyio
async def test_handle_email_with_template_reason():
    job = Job(
        type=JobType.EMAIL_SEND,
        payload={
            "to": "user@example.com",
            "reason": "template:user_notification.html",
            "context": {
                "subject": "Welcome",
                "template_name": "user_notification.html",
                "template_context": {"name": "User"},
            },
        },
    )

    with patch(
        "app.jobs.composer.render_email_template", return_value="<p>Rendered</p>"
    ), patch(
        "app.jobs.handlers.email_service.send_async", new=AsyncMock()
    ) as send_async:
        await handle_email(job)

    send_async.assert_awaited_once_with("user@example.com", "Welcome", "<p>Rendered</p>")
