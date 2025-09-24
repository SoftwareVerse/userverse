"""Translate job reasons into email content."""

from __future__ import annotations

from typing import Any, Dict, Tuple

from app.utils.email.renderer import render_email_template


def render_email(reason: str, context: Dict[str, Any]) -> Tuple[str, str]:
    """Return the subject and HTML body for a given email reason."""

    if reason == "rendered":
        subject = context.get("subject")
        html_body = context.get("html_body")
        if subject is None or html_body is None:
            raise ValueError("Rendered email requires 'subject' and 'html_body'")
        return subject, html_body

    if reason.startswith("template:"):
        template_name = reason.split(":", 1)[1] or context.get("template_name")
    else:
        template_name = context.get("template_name")

    if not template_name:
        raise ValueError(f"Unknown email reason '{reason}' and no template provided")

    template_context = context.get("template_context", {})
    subject = context.get("subject", "")
    html_body = render_email_template(template_name, template_context)
    return subject, html_body
