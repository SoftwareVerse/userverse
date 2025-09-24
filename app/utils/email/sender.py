import click
import logging
import smtplib
import socket
import time
from email.message import EmailMessage
from typing import Any, Dict, Optional

from bs4 import BeautifulSoup
from prometheus_client import Counter

from app.jobs import JobType, get_bus
from app.utils.config.email_config import EmailConfig

logger = logging.getLogger(__name__)

EMAIL_SEND_ATTEMPTS = Counter(
    "email_send_attempts_total",
    "Total number of SMTP send attempts",
    ["reason"],
)
EMAIL_SEND_FAILURES = Counter(
    "email_send_failures_total",
    "Total number of SMTP send failures",
    ["reason", "stage"],
)


def _render_plain_text(
    html_body: str, header: str, to: Optional[str] = None, subject: Optional[str] = None
) -> None:
    """Render HTML content to stdout so developers can see the email body."""
    soup = BeautifulSoup(html_body, "html.parser")
    click.echo(click.style(header, fg="yellow"))
    if to:
        click.echo(f"To: {to}")
    if subject:
        click.echo(f"Subject: {subject}")
    click.echo(soup.get_text(separator="\n", strip=True))


def send_email(
    to: str,
    subject: str,
    html_body: str,
    *,
    reason: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
) -> None:
    """Enqueue an email job if the bus is available, fallback to sync send."""

    job_context = dict(context or {})
    job_context.setdefault("subject", subject)
    job_context.setdefault("html_body", html_body)
    email_reason = reason or job_context.get("reason") or "rendered"

    bus = get_bus()
    if bus:
        try:
            bus.enqueue(
                JobType.EMAIL_SEND,
                {
                    "to": to,
                    "reason": email_reason,
                    "context": job_context,
                },
            )
            logger.info(
                "Email enqueued for background delivery",
                extra={
                    "extra": {
                        "email_to": to,
                        "reason": email_reason,
                        "delivery_mode": "job_bus",
                    }
                },
            )
            return
        except RuntimeError as exc:
            logger.warning("Failed to enqueue email job (%s); sending synchronously", exc)

    deliver_email(to, subject, html_body, reason=email_reason)


def deliver_email(
    to: str,
    subject: str,
    html_body: str,
    *,
    reason: str = "rendered",
    timeout: float = 10.0,
    max_retries: int = 3,
) -> None:
    """Send the email immediately using SMTP with retries and instrumentation."""

    email_settings = EmailConfig.load()

    if not email_settings:
        logger.info(
            "Email config unavailable; skipping SMTP delivery",
            extra={
                "extra": {
                    "email_to": to,
                    "reason": reason,
                    "stage": "config",
                }
            },
        )
        _render_plain_text(
            html_body,
            header="Email config not available. Showing plain text:",
            to=to,
            subject=subject,
        )
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = email_settings.username
    msg["To"] = to
    msg.set_content("This email requires an HTML-compatible client.")
    msg.add_alternative(html_body, subtype="html")

    transient_reasons = {
        socket.timeout: "timeout",
        smtplib.SMTPServerDisconnected: "server_disconnected",
        smtplib.SMTPConnectError: "connect_error",
        smtplib.SMTPDataError: "data_error",
        smtplib.SMTPRecipientsRefused: "recipient_refused",
        smtplib.SMTPResponseException: "smtp_response",
    }
    transient_classes = tuple(transient_reasons.keys())

    last_error: Optional[BaseException] = None

    for attempt in range(1, max_retries + 1):
        EMAIL_SEND_ATTEMPTS.labels(reason=reason).inc()
        stage = "connect"
        try:
            logger.info(
                "SMTP connect attempt",
                extra={
                    "extra": {
                        "email_to": to,
                        "reason": reason,
                        "attempt": attempt,
                        "stage": stage,
                        "host": email_settings.host,
                        "port": email_settings.port,
                    }
                },
            )
            with smtplib.SMTP_SSL(
                email_settings.host,
                email_settings.port,
                timeout=timeout,
            ) as smtp:
                logger.info(
                    "SMTP connected",
                    extra={
                        "extra": {
                            "email_to": to,
                            "reason": reason,
                            "attempt": attempt,
                            "stage": stage,
                        }
                    },
                )
                stage = "auth"
                smtp.login(
                    email_settings.username,
                    email_settings.password,
                )
                logger.info(
                    "SMTP authenticated",
                    extra={
                        "extra": {
                            "email_to": to,
                            "reason": reason,
                            "attempt": attempt,
                            "stage": stage,
                        }
                    },
                )
                stage = "send"
                smtp.send_message(msg)
                logger.info(
                    "SMTP send complete",
                    extra={
                        "extra": {
                            "email_to": to,
                            "reason": reason,
                            "attempt": attempt,
                            "stage": stage,
                        }
                    },
                )
                return
        except socket.gaierror as exc:
            failure_reason = "dns_error"
            EMAIL_SEND_FAILURES.labels(reason=failure_reason, stage=stage).inc()
            logger.warning(
                "SMTP host resolution failed",
                extra={
                    "extra": {
                        "email_to": to,
                        "reason": reason,
                        "stage": stage,
                        "error": str(exc),
                        "host": email_settings.host,
                        "port": email_settings.port,
                    }
                },
            )
            _render_plain_text(
                html_body,
                header=(
                    f"Unable to reach SMTP host {email_settings.host}. Showing plain text:"
                ),
                to=to,
                subject=subject,
            )
            return
        except smtplib.SMTPAuthenticationError as exc:
            failure_reason = "auth"
            EMAIL_SEND_FAILURES.labels(reason=failure_reason, stage=stage).inc()
            logger.error(
                "SMTP authentication failed",
                extra={
                    "extra": {
                        "email_to": to,
                        "reason": reason,
                        "stage": stage,
                        "error": str(exc),
                    }
                },
            )
            raise
        except transient_classes as exc:  # type: ignore[arg-type]
            failure_reason = next(
                (label for cls, label in transient_reasons.items() if isinstance(exc, cls)),
                "transient_error",
            )
            EMAIL_SEND_FAILURES.labels(reason=failure_reason, stage=stage).inc()
            logger.warning(
                "Transient SMTP error",
                extra={
                    "extra": {
                        "email_to": to,
                        "reason": reason,
                        "stage": stage,
                        "attempt": attempt,
                        "error": str(exc),
                    }
                },
            )
            last_error = exc
        except smtplib.SMTPException as exc:
            failure_reason = "smtp_error"
            EMAIL_SEND_FAILURES.labels(reason=failure_reason, stage=stage).inc()
            logger.error(
                "SMTP error",
                extra={
                    "extra": {
                        "email_to": to,
                        "reason": reason,
                        "stage": stage,
                        "attempt": attempt,
                        "error": str(exc),
                    }
                },
            )
            last_error = exc
        except Exception as exc:  # noqa: BLE001 - unexpected but logged
            failure_reason = "unexpected"
            EMAIL_SEND_FAILURES.labels(reason=failure_reason, stage=stage).inc()
            logger.error(
                "Unexpected error sending email",
                extra={
                    "extra": {
                        "email_to": to,
                        "reason": reason,
                        "stage": stage,
                        "attempt": attempt,
                        "error": str(exc),
                    }
                },
            )
            raise

        if attempt >= max_retries:
            if last_error is not None:
                raise last_error
            raise RuntimeError("SMTP delivery failed after retries")

        backoff_seconds = min(10.0, 2 ** (attempt - 1))
        logger.info(
            "Retrying SMTP send after backoff",
            extra={
                "extra": {
                    "email_to": to,
                    "reason": reason,
                    "stage": stage,
                    "attempt": attempt,
                    "backoff_seconds": backoff_seconds,
                }
            },
        )
        time.sleep(backoff_seconds)
