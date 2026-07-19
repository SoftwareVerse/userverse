from datetime import timedelta
from typing import Optional

from fastapi import BackgroundTasks, status
from sqlalchemy.orm import Session
from app.models.generic_response import GenericResponseModel
from app.repository.user import UserRepository
from app.api.security.jwt import JWTManager
from app.services.mailer import MailService
from app.utils.app_error import AppError
from app.utils.logging import logger
from app.models.user.account_status import UserAccountStatus
from app.models.user.response_messages import UserResponseMessages
from app.utils.rate_limiter import (
    RateLimitExceeded,
    VERIFICATION_EMAIL_RATE_LIMITER,
)


class UserVerificationService:
    """
    Service for handling user account verification via JWT tokens.
    This service does not require an authenticated context to run.
    """

    VERIFICATION_TOKEN_EXPIRY_MINUTES = 60 * 24
    ACCOUNT_REGISTRATION_SUBJECT = "User Account Registration"
    VERIFICATION_REMINDER_SUBJECT = "Verify Your Email Address"
    ACCOUNT_NOTIFICATION_TEMPLATE = "user_notification.html"

    def __init__(self, session: Session):
        self.session = session

    def verify_user_account(self, token: str) -> str:
        """
        Verifies a user account using a JWT email verification token.
        This method runs without requiring an authenticated context.
        """
        payload = JWTManager().decode_verification_token(token)

        email = payload.get("sub")
        token_type = payload.get("type")

        if not email:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=UserResponseMessages.EMAIL_VERIFICATION_FAILED.value,
            )

        if token_type != "verification":
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=UserResponseMessages.INVALID_VERIFICATION_TOKEN.value,
            )

        user_repository = UserRepository(self.session)
        user = user_repository.get_user_by_email(email)

        if user.status == UserAccountStatus.ACTIVE.name_value:
            return UserResponseMessages.USER_ACCOUNT_ALREADY_ACTIVE.value

        if user.status != UserAccountStatus.AWAITING_VERIFICATION.name_value:
            raise AppError(
                status_code=status.HTTP_403_FORBIDDEN,
                message="User account is not awaiting verification",
            )

        user_repository.update_user_status(
            user_id=user.id,
            account_status=UserAccountStatus.ACTIVE.name_value,
        )

        return UserResponseMessages.USER_ACCOUNT_VERIFIED.value

    def resend_verification_email(
        self,
        user_email: str,
        *,
        server_url: str,
        app_name: str,
        verification_required: bool,
        client_ip: Optional[str] = None,
        background_tasks: Optional[BackgroundTasks] = None,
    ) -> GenericResponseModel[None]:
        sanitized_ip = client_ip or "unknown"

        try:
            VERIFICATION_EMAIL_RATE_LIMITER.check(
                email=user_email, ip_address=sanitized_ip
            )
        except RateLimitExceeded as exc:
            logger.warning(
                "Verification resend rate limit hit",
                extra={
                    "extra": {
                        "email": user_email,
                        "client_ip": sanitized_ip,
                        "retry_after": getattr(exc, "retry_after", None),
                    }
                },
            )
            raise AppError(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                message=UserResponseMessages.VERIFICATION_RATE_LIMITED.value,
                error="verification_email_rate_limited",
                log_error=False,
            ) from exc

        if not verification_required:
            return GenericResponseModel(
                message=UserResponseMessages.VERIFICATION_EMAIL_RESENT.value,
                data=None,
            )

        session_user = UserRepository(self.session).get_user_record_by_email(user_email)
        if not session_user:
            logger.info(
                "Verification resend requested for unknown email",
                extra={"extra": {"email": user_email, "client_ip": sanitized_ip}},
            )
            return GenericResponseModel(
                message=UserResponseMessages.VERIFICATION_EMAIL_RESENT.value,
                data=None,
            )

        status_value = (session_user.primary_meta_data or {}).get("status")
        if status_value != UserAccountStatus.AWAITING_VERIFICATION.name_value:
            logger.info(
                "Verification resend skipped for non-pending account",
                extra={
                    "extra": {
                        "email": session_user.email,
                        "client_ip": sanitized_ip,
                        "status": status_value,
                    }
                },
            )
            return GenericResponseModel(
                message=UserResponseMessages.VERIFICATION_EMAIL_RESENT.value,
                data=None,
            )

        token = JWTManager().sign_payload(
            {"sub": session_user.email, "type": "verification"},
            expires_delta=timedelta(minutes=self.VERIFICATION_TOKEN_EXPIRY_MINUTES),
        )
        verification_link = f"{server_url.rstrip('/')}/user/verify?token={token}"
        subject = self.VERIFICATION_REMINDER_SUBJECT
        full_name = " ".join(
            part.strip()
            for part in [session_user.first_name or "", session_user.last_name or ""]
            if part and part.strip()
        )
        email_context = {
            "template_name": subject,
            "user_name": full_name,
            "app_name": app_name,
            "verification_link": verification_link,
            "mode": "verify",
        }

        if background_tasks is not None:
            background_tasks.add_task(
                MailService.send_template_email,
                to=session_user.email,
                subject=subject,
                template_name=self.ACCOUNT_NOTIFICATION_TEMPLATE,
                context=email_context,
            )
        else:
            try:
                MailService.send_template_email(
                    to=session_user.email,
                    subject=subject,
                    template_name=self.ACCOUNT_NOTIFICATION_TEMPLATE,
                    context=email_context,
                )
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "Verification email dispatch failed",
                    extra={
                        "extra": {
                            "email": session_user.email,
                            "client_ip": sanitized_ip,
                            "error": str(exc),
                        }
                    },
                )

        return GenericResponseModel(
            message=UserResponseMessages.VERIFICATION_EMAIL_RESENT.value,
            data=None,
        )
