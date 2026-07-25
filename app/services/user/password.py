import random
import secrets
import string
from datetime import timedelta
from typing import Optional
from urllib.parse import urlencode

from fastapi import BackgroundTasks, status
from sqlalchemy.orm import Session

from app.configs import settings
from app.models.generic_response import GenericResponseModel
from app.models.user.password import PasswordResetMethod
from app.models.user.response_messages import (
    PasswordResetResponseMessages,
    UserResponseMessages,
)
from app.repository.user import UserRepository
from app.repository.user_password import UserPasswordRepository
from app.services.mailer import MailService
from app.utils.app_error import AppError
from app.utils.logging import logger
from app.utils.rate_limiter import (
    PASSWORD_RESET_RATE_LIMITER,
    RateLimitExceeded,
)


class UserPasswordService:
    SEND_OTP_EMAIL_TEMPLATE = "reset_user_password.html"
    SEND_MAGIC_LINK_EMAIL_TEMPLATE = "reset_user_password_magic_link.html"
    OTP_EMAIL_SUBJECT = "Password Reset OTP"
    MAGIC_LINK_EMAIL_SUBJECT = "Password Reset Link"

    @classmethod
    def generate_random_string(cls, length=10):
        characters = string.ascii_letters + string.digits
        return "".join(random.choice(characters) for _ in range(length))

    @staticmethod
    def generate_magic_link_token() -> str:
        return secrets.token_urlsafe(32)

    def __init__(self, session: Session):
        self.session = session

    @property
    def password_reset_expiry(self) -> timedelta:
        return timedelta(minutes=settings.PASSWORD_RESET_EXPIRY_MINUTES)

    @staticmethod
    def build_magic_reset_url(token: str) -> str:
        frontend_url = settings.FRONTEND_URL
        if not frontend_url:
            raise AppError(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=PasswordResetResponseMessages.FRONTEND_URL_NOT_CONFIGURED.value,
                error="frontend_url_not_configured",
            )
        return f"{frontend_url}?{urlencode({'token': token})}"

    def _build_email_context(
        self,
        *,
        method: PasswordResetMethod,
        token: str,
        user_name: str,
    ) -> dict[str, str]:
        context = {
            "user_name": user_name,
            "app_name": settings.APP_NAME,
        }
        if method == PasswordResetMethod.OTP:
            context["otp"] = token
            return context

        context["reset_url"] = self.build_magic_reset_url(token)
        context["expires_in"] = f"{settings.PASSWORD_RESET_EXPIRY_MINUTES} minutes"
        return context

    def request_password_reset(
        self,
        user_email: str,
        *,
        method: PasswordResetMethod = PasswordResetMethod.OTP,
        client_ip: Optional[str] = None,
        background_tasks: Optional[BackgroundTasks] = None,
    ) -> GenericResponseModel:
        """
        Request a password reset by sending an OTP or magic link to the user's email.
        """
        sanitized_ip = client_ip or "unknown"

        if method == PasswordResetMethod.MAGIC_LINK:
            self.build_magic_reset_url("placeholder")

        try:
            PASSWORD_RESET_RATE_LIMITER.check(email=user_email, ip_address=sanitized_ip)
        except RateLimitExceeded as exc:
            logger.warning(
                "Password reset rate limit hit",
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
                message=PasswordResetResponseMessages.RATE_LIMITED.value,
                error="password_reset_rate_limited",
                log_error=False,
            ) from exc

        session_user = UserRepository(self.session).get_user_record_by_email(user_email)
        if not session_user:
            logger.info(
                "Password reset requested for unknown email",
                extra={"extra": {"email": user_email, "client_ip": sanitized_ip}},
            )
            return GenericResponseModel(
                message=PasswordResetResponseMessages.OTP_SENT.value,
                data=None,
            )

        token = (
            self.generate_random_string(length=6)
            if method == PasswordResetMethod.OTP
            else self.generate_magic_link_token()
        )
        user_password_repository = UserPasswordRepository(self.session)
        user_password_repository.create_password_reset_record(
            user_email=session_user.email,
            method=method,
            token=token,
            expires_in=self.password_reset_expiry,
        )

        full_name = " ".join(
            part.strip()
            for part in [session_user.first_name or "", session_user.last_name or ""]
            if part and part.strip()
        )
        email_context = self._build_email_context(
            method=method,
            token=token,
            user_name=full_name or session_user.email,
        )
        subject = (
            self.OTP_EMAIL_SUBJECT
            if method == PasswordResetMethod.OTP
            else self.MAGIC_LINK_EMAIL_SUBJECT
        )
        template_name = (
            self.SEND_OTP_EMAIL_TEMPLATE
            if method == PasswordResetMethod.OTP
            else self.SEND_MAGIC_LINK_EMAIL_TEMPLATE
        )

        if background_tasks is not None:
            background_tasks.add_task(
                MailService.send_template_email,
                to=session_user.email,
                subject=subject,
                template_name=template_name,
                context=email_context,
            )
        else:
            try:
                MailService.send_template_email(
                    to=session_user.email,
                    subject=subject,
                    template_name=template_name,
                    context=email_context,
                )
            except Exception as exc:  # noqa: BLE001 - log and move on
                logger.error(
                    "Password reset email dispatch failed",
                    extra={
                        "extra": {
                            "email": session_user.email,
                            "client_ip": sanitized_ip,
                            "error": str(exc),
                        }
                    },
                )

        return GenericResponseModel(
            message=PasswordResetResponseMessages.OTP_SENT.value,
            data=None,
        )

    def validate_otp_and_change_password(
        self, user_email: str, otp: str, new_password
    ) -> GenericResponseModel:
        """
        Validate the OTP sent to the user's email and change the password.
        """
        user_repository = UserRepository(self.session)
        user = user_repository.get_user_by_email(user_email)
        if not user:
            raise ValueError(UserResponseMessages.USER_NOT_FOUND.value)

        user_password_repository = UserPasswordRepository(self.session)
        if user_password_repository.verify_password_reset_token(
            user_email=user.email,
            method=PasswordResetMethod.OTP,
            token=otp,
        ):
            user_password_repository.update_password(
                user_email=user.email,
                new_password=new_password,
            )
            return GenericResponseModel(
                message=PasswordResetResponseMessages.PASSWORD_CHANGED.value,
                data=None,
            )

        raise AppError(
            status_code=400,
            message=PasswordResetResponseMessages.OTP_VERIFICATION_FAILED.value,
            error=PasswordResetResponseMessages.ERROR.value,
        )

    def reset_password_with_token(
        self,
        *,
        token: str,
        new_password: str,
    ) -> GenericResponseModel:
        user_repository = UserRepository(self.session)
        user = user_repository.get_user_record_by_password_reset_token(
            token=token,
            method=PasswordResetMethod.MAGIC_LINK,
        )

        if not user:
            raise AppError(
                status_code=400,
                message=PasswordResetResponseMessages.MAGIC_LINK_VERIFICATION_FAILED.value,
                error=PasswordResetResponseMessages.TOKEN_ERROR.value,
            )

        user_password_repository = UserPasswordRepository(self.session)
        if not user_password_repository.verify_password_reset_token(
            user_email=user.email,
            method=PasswordResetMethod.MAGIC_LINK,
            token=token,
        ):
            raise AppError(
                status_code=400,
                message=PasswordResetResponseMessages.MAGIC_LINK_VERIFICATION_FAILED.value,
                error=PasswordResetResponseMessages.TOKEN_ERROR.value,
            )

        user_password_repository.update_password(
            user_email=user.email,
            new_password=new_password,
        )
        return GenericResponseModel(
            message=PasswordResetResponseMessages.PASSWORD_CHANGED.value,
            data=None,
        )
