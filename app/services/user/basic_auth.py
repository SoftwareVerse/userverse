from datetime import timedelta
from typing import Optional

from fastapi import BackgroundTasks

from app.services.mailer import MailService
from app.models.user.account_status import UserAccountStatus
from app.models.user.response_messages import UserResponseMessages
from app.models.user.user import (
    TokenResponseModel,
    UserCreateModel,
    UserLoginModel,
    UserReadModel,
)
from app.repository.user import UserRepository
from app.api.security.jwt import JWTManager
from app.utils.app_error import AppError
from app.utils.hash_password import hash_password
from app.utils.logging import logger
from app.utils.shared_context import SharedContext


class UserBasicAuthService:
    ACCOUNT_REGISTRATION_SUBJECT = "User Account Registration"
    VERIFICATION_REMINDER_SUBJECT = "Verify Your Email Address"
    ACCOUNT_NOTIFICATION_TEMPLATE = "user_notification.html"
    VERIFICATION_TOKEN_EXPIRY_MINUTES = 60 * 24

    def __init__(self, context: SharedContext):
        self.context = context
        self.user_repository = UserRepository(context.db_session)

    def _ensure_user_is_active(self, user: UserReadModel) -> None:
        allowed_statuses = {UserAccountStatus.ACTIVE.name_value}
        if not self.context.configs.REQUIRE_EMAIL_VERIFICATION:
            allowed_statuses.add(UserAccountStatus.AWAITING_VERIFICATION.name_value)

        if user.status not in allowed_statuses:
            raise AppError(
                status_code=403,
                message=UserResponseMessages.USER_ACCOUNT_INACTIVE.value,
            )

    def _resend_verification_email_for_pending_login(self, user: UserReadModel) -> None:
        if not self.context.configs.REQUIRE_EMAIL_VERIFICATION:
            return
        if user.status != UserAccountStatus.AWAITING_VERIFICATION.name_value:
            return

        self.context.user = user
        self.send_verification_email(mode="verify")

    def generate_verification_link(self) -> str:
        token = JWTManager().sign_payload(
            {"sub": self.context.get_user_email(), "type": "verification"},
            expires_delta=timedelta(minutes=self.VERIFICATION_TOKEN_EXPIRY_MINUTES),
        )
        server_url = self.context.configs.SERVER_URL
        return f"{server_url}/user/verify?token={token}"

    def send_verification_email(
        self,
        mode: str = "create",
        *,
        background_tasks: Optional[BackgroundTasks] = None,
    ) -> None:
        user = self.context.get_user()
        verification_link = self.generate_verification_link()
        subject = (
            self.ACCOUNT_REGISTRATION_SUBJECT
            if mode == "create"
            else self.VERIFICATION_REMINDER_SUBJECT
        )
        template_context = {
            "template_name": subject,
            "user_name": f"{user.first_name or ''} {user.last_name or ''}",
            "app_name": self.context.configs.APP_NAME,
            "verification_link": verification_link,
            "mode": mode,
        }

        if background_tasks is not None:
            background_tasks.add_task(
                MailService.send_template_email,
                to=user.email,
                subject=subject,
                template_name=self.ACCOUNT_NOTIFICATION_TEMPLATE,
                context=template_context,
            )
            return

        try:
            MailService.send_template_email(
                to=user.email,
                subject=subject,
                template_name=self.ACCOUNT_NOTIFICATION_TEMPLATE,
                context=template_context,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Verification email dispatch failed",
                extra={
                    "extra": {
                        "email": user.email,
                        "mode": mode,
                        "error": str(exc),
                    }
                },
            )

    def user_login(self, user_credentials: UserLoginModel):
        user = self.user_repository.get_user_by_email(
            user_credentials.email, user_credentials.password
        )
        self._resend_verification_email_for_pending_login(user)
        self._ensure_user_is_active(user)
        refresh_token_version = self.user_repository.get_refresh_token_version(user.id)
        return JWTManager().sign_jwt(user, refresh_token_version=refresh_token_version)

    def refresh_user_token(self, refresh_token: str) -> TokenResponseModel:
        jwt_manager = JWTManager()
        token_user, _ = jwt_manager.decode_refresh_token(refresh_token)
        current_user = self.user_repository.get_user_by_id(token_user.id)
        self._ensure_user_is_active(current_user)
        refresh_token_version = self.user_repository.get_refresh_token_version(
            current_user.id
        )
        return jwt_manager.refresh_token(
            refresh_token,
            user=current_user,
            refresh_token_version=refresh_token_version,
        )

    def revoke_refresh_token(self, refresh_token: str) -> None:
        token_user, _ = JWTManager().decode_refresh_token(refresh_token)
        current_user = self.user_repository.get_user_by_id(token_user.id)
        self.user_repository.increment_refresh_token_version(current_user.id)

    def create_user(
        self,
        user_credentials: UserLoginModel,
        user_data: UserCreateModel,
        *,
        background_tasks: Optional[BackgroundTasks] = None,
    ) -> UserReadModel:
        account_status = (
            UserAccountStatus.AWAITING_VERIFICATION.name_value
            if self.context.configs.REQUIRE_EMAIL_VERIFICATION
            else UserAccountStatus.ACTIVE.name_value
        )
        data = {
            "first_name": user_data.first_name,
            "last_name": user_data.last_name,
            "email": user_credentials.email,
            "phone_number": user_data.phone_number,
            "password": hash_password(user_credentials.password),
        }
        user = self.user_repository.create_user(data, account_status=account_status)
        self.context.user = user
        if self.context.configs.REQUIRE_EMAIL_VERIFICATION:
            self.send_verification_email(
                mode="create", background_tasks=background_tasks
            )
        return user
