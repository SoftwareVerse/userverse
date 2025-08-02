from fastapi import status
from datetime import timedelta
from typing import Optional

# utils
from app.logic.company.repository.company import CompanyRepository
from app.logic.mailer import MailService
from app.models.company.company import CompanyQueryParams
from app.models.user.account_status import UserAccountStatus
from app.security.jwt import JWTManager
from app.utils.app_error import AppError

# repository
from app.repository.user import UserRepository

# models
from app.models.user.user import (
    UserCreateModel,
    UserUpdateModel,
    UserReadModel,
    UserLoginModel,
    TokenResponseModel,
)
from app.models.user.response_messages import UserResponseMessages
from app.utils.hash_password import hash_password


class UserService:
    ACCOUNT_REGISTRATION_SUBJECT = "User Account Registration"
    ACCOUNT_NOTIFICATION_TEMPLATE = "user_notification.html"

    VERIFICATION_TOKEN_EXPIRY_MINUTES = 60 * 24  # 1 day
    ACCOUNT_VERIFICATION_SUBJECT = "User Account Verification"

    @classmethod
    def generate_verification_link(cls, user: UserReadModel) -> str:
        token = JWTManager().sign_payload(
            {"sub": user.email, "type": "verification"},
            expires_delta=timedelta(minutes=cls.VERIFICATION_TOKEN_EXPIRY_MINUTES),
        )
        return f"https://yourdomain.com/api/v1/user/verify?token={token}"

    @classmethod
    def send_verification_email(cls, user: UserReadModel, mode: str = "create"):
        verification_link = cls.generate_verification_link(user)
        MailService.send_template_email(
            to=user.email,
            subject=cls.ACCOUNT_REGISTRATION_SUBJECT,
            template_name=cls.ACCOUNT_NOTIFICATION_TEMPLATE,
            context={
                "template_name": cls.ACCOUNT_REGISTRATION_SUBJECT,
                "user_name": f"{user.first_name or ''} {user.last_name or ''}",
                "verification_link": verification_link,
                "mode": mode,
            },
        )

    @classmethod
    def verify_user_account(cls, token: str) -> str:
        """
        Verify user account using the provided JWT token.
        The token should contain the user's email as the subject.
        """
        payload = JWTManager().decode_token(token)

        if (
            not payload
            or payload.status != UserAccountStatus.AWAITING_VERIFICATION.name_value
        ):
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Invalid or expired verification token",
            )

        email = payload.email
        if not email:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Token missing subject (email)",
            )

        # Update the user's account status
        user_repository = UserRepository()
        user = user_repository.get_user_by_email(email)
        user_repository.update_user_status(
            user_id=user.id,
            account_status=UserAccountStatus.ACTIVE.name_value,
        )

        return UserResponseMessages.USER_ACCOUNT_VERIFIED.value

    @staticmethod
    def user_login(user_credentials: UserLoginModel) -> TokenResponseModel:
        user_repository = UserRepository()
        user = user_repository.get_user_by_email(
            user_credentials.email, hash_password(user_credentials.password)
        )
        if not user:
            raise AppError(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message=UserResponseMessages.INVALID_CREDENTIALS.value,
            )
        return JWTManager().sign_jwt(user)

    @classmethod
    def create_user(
        cls, user_credentials: UserLoginModel, user_data: UserCreateModel
    ) -> UserReadModel:
        user_repository = UserRepository()
        data = {
            "first_name": user_data.first_name,
            "last_name": user_data.last_name,
            "email": user_credentials.email,
            "phone_number": user_data.phone_number,
            "password": hash_password(user_credentials.password),
        }
        user = user_repository.create_user(data)

        # Send verification email
        cls.send_verification_email(user, mode="create")

        return user

    @staticmethod
    def get_user_companies(
        params: CompanyQueryParams,
        user: UserReadModel,
    ):
        company_repository = CompanyRepository()
        return company_repository.get_user_companies(user_id=user.id, params=params)

    @staticmethod
    def get_user(
        user_id: Optional[int] = None, user_email: Optional[str] = None
    ) -> UserReadModel:
        user_repository = UserRepository()
        if user_id:
            return user_repository.get_user_by_id(user_id)
        elif user_email:
            return user_repository.get_user_by_email(user_email)
        else:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=UserResponseMessages.USER_NOT_FOUND.value,
            )

    @classmethod
    def update_user(cls, user_id, user_data: UserUpdateModel):
        data = {}
        if user_data.first_name:
            data["first_name"] = user_data.first_name
        if user_data.last_name:
            data["last_name"] = user_data.last_name
        if user_data.phone_number:
            data["phone_number"] = user_data.phone_number
        if user_data.password:
            data["password"] = hash_password(user_data.password)

        if not data:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=UserResponseMessages.INVALID_REQUEST_MESSAGE.value,
            )
        user_repository = UserRepository()
        return user_repository.update_user(user_id, data)
