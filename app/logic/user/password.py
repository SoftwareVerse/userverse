import random
import string
from typing import Optional

from fastapi import BackgroundTasks, status

# models
from app.logic.mailer import MailService
from app.models.generic_response import GenericResponseModel

# repository
from app.repository.user_password import UserPasswordRepository
from sqlalchemy.orm import Session

# UTILS
from app.models.user.response_messages import (
    PasswordResetResponseMessages,
    UserResponseMessages,
)
from app.utils.app_error import AppError
from app.utils.logging import logger
from app.utils.rate_limiter import (
    PASSWORD_RESET_RATE_LIMITER,
    RateLimitExceeded,
)
from app.database.user import User
from app.repository.user import UserRepository


class UserPasswordService:
    SEND_OTP_EMAIL_TEMPLATE = "reset_user_password.html"
    OTP_EMAIL_SUBJECT = "Password Reset OTP"

    @classmethod
    def generate_random_string(cls, length=10):
        characters = string.ascii_letters + string.digits
        return "".join(random.choice(characters) for _ in range(length))

    def __init__(self, session: Session):
        self.session = session

    def request_password_reset(
        self,
        user_email: str,
        *,
        client_ip: Optional[str] = None,
        background_tasks: Optional[BackgroundTasks] = None,
    ) -> GenericResponseModel:
        """
        Request a password reset by sending an OTP to the user's email.
        """
        sanitized_ip = client_ip or "unknown"

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

        # check if user exists without leaking enumeration through HTTP response
        session_user = (
            self.session.query(User).filter(User.email == user_email).first()
        )
        if not session_user:
            logger.info(
                "Password reset requested for unknown email",
                extra={"extra": {"email": user_email, "client_ip": sanitized_ip}},
            )
            return GenericResponseModel(
                message=PasswordResetResponseMessages.OTP_SENT.value,
                data=None,
            )

        # reset token
        token = self.generate_random_string(length=6)
        # populate the token in the database for the user
        user_password_repository = UserPasswordRepository(self.session)
        user_password_repository.update_password_reset_token(
            user_email=session_user.email,
            token=token,
        )
        # send email asynchronously; failures must not affect the HTTP response
        full_name = " ".join(
            part.strip()
            for part in [session_user.first_name or "", session_user.last_name or ""]
            if part and part.strip()
        )
        email_context = {
            "user_name": full_name,
            "otp": token,
        }
        if background_tasks is not None:
            background_tasks.add_task(
                MailService.send_template_email,
                to=session_user.email,
                subject=self.OTP_EMAIL_SUBJECT,
                template_name=self.SEND_OTP_EMAIL_TEMPLATE,
                context=email_context,
            )
        else:
            try:
                MailService.send_template_email(
                    to=session_user.email,
                    subject=self.OTP_EMAIL_SUBJECT,
                    template_name=self.SEND_OTP_EMAIL_TEMPLATE,
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
        Validate the OTP sent to the user's email. Ensure that the OTP is valid and not expired.
        Return token for the next step(Change Password).
        """
        # check if user exists
        user_repository = UserRepository(self.session)
        user = user_repository.get_user_by_email(user_email)
        if not user:
            raise ValueError(UserResponseMessages.USER_NOT_FOUND.value)

        # populate the token in the database for the user
        user_password_repository = UserPasswordRepository(self.session)
        if user_password_repository.verify_password_reset_token(
            user_email=user.email,
            token=otp,
        ):
            # OTP is valid, proceed to change password
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
