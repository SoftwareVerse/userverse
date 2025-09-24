from datetime import timedelta
from typing import Optional

from fastapi import BackgroundTasks

from app.logic.mailer import MailService
from app.models.user.response_messages import UserResponseMessages
from app.models.user.user import UserCreateModel, UserLoginModel, UserReadModel
from app.repository.user import UserRepository
from app.security.jwt import JWTManager
from app.utils.app_error import AppError
from app.utils.hash_password import hash_password
from app.utils.logging import logger
from app.utils.shared_context import SharedContext


class UserBasicAuthService:
    ACCOUNT_REGISTRATION_SUBJECT = "User Account Registration"
    ACCOUNT_NOTIFICATION_TEMPLATE = "user_notification.html"
    VERIFICATION_TOKEN_EXPIRY_MINUTES = 60 * 24

    def __init__(self, context: SharedContext):
        self.context = context
        self.user_repository = UserRepository(context.db_session)

    def generate_verification_link(self) -> str:
        token = JWTManager().sign_payload(
            {"sub": self.context.get_user_email(), "type": "verification"},
            expires_delta=timedelta(minutes=self.VERIFICATION_TOKEN_EXPIRY_MINUTES),
        )
        server_url = self.context.configs.get("server_url", "http://localhost:8000")
        return f"{server_url}/user/verify?token={token}"

    def send_verification_email(
        self,
        mode: str = "create",
        *,
        background_tasks: Optional[BackgroundTasks] = None,
    ) -> None:
        user = self.context.get_user()
        verification_link = self.generate_verification_link()
        template_context = {
            "template_name": self.ACCOUNT_REGISTRATION_SUBJECT,
            "user_name": f"{user.first_name or ''} {user.last_name or ''}",
            "verification_link": verification_link,
            "mode": mode,
        }

        if background_tasks is not None:
            background_tasks.add_task(
                MailService.send_template_email,
                to=user.email,
                subject=self.ACCOUNT_REGISTRATION_SUBJECT,
                template_name=self.ACCOUNT_NOTIFICATION_TEMPLATE,
                context=template_context,
            )
            return

        try:
            MailService.send_template_email(
                to=user.email,
                subject=self.ACCOUNT_REGISTRATION_SUBJECT,
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
        if not user:
            raise AppError(
                status_code=401,
                message=UserResponseMessages.INVALID_CREDENTIALS.value,
            )
        return JWTManager().sign_jwt(user)

    def create_user(
        self,
        user_credentials: UserLoginModel,
        user_data: UserCreateModel,
        *,
        background_tasks: Optional[BackgroundTasks] = None,
    ) -> UserReadModel:
        data = {
            "first_name": user_data.first_name,
            "last_name": user_data.last_name,
            "email": user_credentials.email,
            "phone_number": user_data.phone_number,
            "password": hash_password(user_credentials.password),
        }
        user = self.user_repository.create_user(data)
        self.context.user = user
        self.send_verification_email(
            mode="create", background_tasks=background_tasks
        )
        return user
