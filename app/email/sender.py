import click
import logging
import smtplib
import socket
import ssl
import time
from ssl import SSLError
from email.message import EmailMessage
from typing import Optional

from bs4 import BeautifulSoup
from prometheus_client import Counter

from app.configs import get_settings
from app.models.configs import EmailSettings

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

TEST_ENVIRONMENTS = {"test_environment", "testing", "test"}


def _load_email_settings() -> Optional[EmailSettings]:
    settings = get_settings()
    if settings.environment in TEST_ENVIRONMENTS:
        logger.warning("Skipping email config in test environment.")
        return None

    email_settings = settings.email
    if not email_settings.model_dump(exclude_none=True):
        logger.warning("Email configuration section is missing.")
        return None

    missing = [
        field
        for field, value in {
            "HOST": email_settings.host,
            "PORT": email_settings.port,
            "USERNAME": email_settings.username,
            "PASSWORD": email_settings.password,
        }.items()
        if not value
    ]
    if missing:
        logger.warning("Missing email config fields: %s", missing)
        return None

    return email_settings


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
) -> None:
    """Send an email immediately via SMTP."""
    email_reason = reason or "rendered"
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
    """
    Send the email immediately using SMTP with retries and instrumentation.

    Supports BOTH:
      - Implicit SSL (SMTPS) on port 465
      - STARTTLS (submission) on port 587 or 25
    Decision order:
      - If email settings expose boolean flags use_ssl/use_starttls, honor them.
      - Otherwise infer from port: 465 => implicit SSL; 587/25 => STARTTLS.
    """

    email_settings = _load_email_settings()

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

    # Exceptions treated as transient (we'll retry)
    transient_reasons = {
        socket.timeout: "timeout",
        smtplib.SMTPServerDisconnected: "server_disconnected",
        smtplib.SMTPConnectError: "connect_error",
        smtplib.SMTPDataError: "data_error",
        smtplib.SMTPRecipientsRefused: "recipient_refused",
        smtplib.SMTPResponseException: "smtp_response",
        smtplib.SMTPNotSupportedError: "tls_unsupported",
        SSLError: "tls_error",
    }
    transient_classes = tuple(transient_reasons.keys())

    # Decide TLS mode.
    # Prefer configured flags from settings (`email_ssl` / `email_tls`) and keep
    # legacy fallbacks (`use_ssl` / `use_starttls`) for compatibility.
    use_implicit_ssl = bool(
        getattr(email_settings, "email_ssl", getattr(email_settings, "use_ssl", False))
    )
    use_starttls = bool(
        getattr(
            email_settings,
            "email_tls",
            getattr(email_settings, "use_starttls", False),
        )
    )

    if not (use_implicit_ssl or use_starttls):
        # Infer from port if flags not provided
        if email_settings.port == 465:
            use_implicit_ssl = True
        elif email_settings.port in (587, 25):
            use_starttls = True

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
                        "mode": (
                            "implicit_ssl"
                            if use_implicit_ssl
                            else ("starttls" if use_starttls else "plain")
                        ),
                    }
                },
            )

            tls_ctx = ssl.create_default_context()

            if use_implicit_ssl:
                # Implicit SSL (port 465)
                with smtplib.SMTP_SSL(
                    email_settings.host,
                    email_settings.port,
                    timeout=timeout,
                    context=tls_ctx,
                ) as smtp:
                    logger.info(
                        "SMTP connected (implicit SSL)",
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
                    smtp.login(email_settings.username, email_settings.password)
                    logger.info(
                        "SMTP authenticated",
                        extra={"extra": {"attempt": attempt, "stage": stage}},
                    )
                    stage = "send"
                    smtp.send_message(msg)
                    logger.info(
                        "SMTP send complete",
                        extra={"extra": {"attempt": attempt, "stage": stage}},
                    )
                    return

            # Plain connect, then optionally STARTTLS
            with smtplib.SMTP(
                email_settings.host, email_settings.port, timeout=timeout
            ) as smtp:
                logger.info(
                    "SMTP connected (plain)",
                    extra={
                        "extra": {
                            "email_to": to,
                            "reason": reason,
                            "attempt": attempt,
                            "stage": stage,
                        }
                    },
                )
                if use_starttls:
                    stage = "starttls"
                    smtp.ehlo()
                    smtp.starttls(context=tls_ctx)
                    smtp.ehlo()
                    logger.info(
                        "STARTTLS negotiated",
                        extra={"extra": {"attempt": attempt, "stage": stage}},
                    )

                stage = "auth"
                smtp.login(email_settings.username, email_settings.password)
                logger.info(
                    "SMTP authenticated",
                    extra={"extra": {"attempt": attempt, "stage": stage}},
                )

                stage = "send"
                smtp.send_message(msg)
                logger.info(
                    "SMTP send complete",
                    extra={"extra": {"attempt": attempt, "stage": stage}},
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
                header=f"Unable to reach SMTP host {email_settings.host}. Showing plain text:",
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
                (
                    label
                    for cls, label in transient_reasons.items()
                    if isinstance(exc, cls)
                ),
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

        except Exception as exc:  # noqa: BLE001
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

        # Backoff & retry
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
