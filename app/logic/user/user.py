from fastapi import status
from datetime import timedelta
from typing import Optional

# Utils
from app.logic.company.repository.company import CompanyRepository
from app.logic.mailer import MailService
from app.models.company.company import CompanyQueryParams
from app.models.user.account_status import UserAccountStatus
from app.security.jwt import JWTManager
from app.utils.app_error import AppError
from app.utils.hash_password import hash_password
from app.utils.shared_context import SharedContext

# Repository
from app.repository.user import UserRepository

# Models
from app.models.user.user import (
    UserCreateModel,
    UserUpdateModel,
    UserReadModel,
    UserLoginModel,
    TokenResponseModel,
)
from app.models.user.response_messages import UserResponseMessages


class UserService:
    """ Service class for user-related operations.
    Handles user account creation, verification, login, and profile management.
    """
    ACCOUNT_REGISTRATION_SUBJECT = "User Account Registration"
    ACCOUNT_NOTIFICATION_TEMPLATE = "user_notification.html"
    VERIFICATION_TOKEN_EXPIRY_MINUTES = 60 * 24  # 1 day

    def __init__(self, context: SharedContext):
        self.context = context
        self.user_repository = UserRepository()
        self.company_repository = CompanyRepository()

    def generate_verification_link(self) -> str:
        """ Generate a verification link for the user. """
        token = JWTManager().sign_payload(
            {"sub": self.context.get_user_email(), "type": "verification"},
            expires_delta=timedelta(minutes=self.VERIFICATION_TOKEN_EXPIRY_MINUTES),
        )

        server_url = self.context.configs.get("server_url", "http://localhost:8000")
        return f"{server_url}/user/verify?token={token}"

    def send_verification_email(self, mode: str = "create"):
        """ Send verification email to the user after account creation or update."""
        user = self.context.get_user()
        verification_link = self.generate_verification_link()
        MailService.send_template_email(
            to=user.email,
            subject=self.ACCOUNT_REGISTRATION_SUBJECT,
            template_name=self.ACCOUNT_NOTIFICATION_TEMPLATE,
            context={
                "template_name": self.ACCOUNT_REGISTRATION_SUBJECT,
                "user_name": f"{user.first_name or ''} {user.last_name or ''}",
                "verification_link": verification_link,
                "mode": mode,
            },
        )

    @staticmethod
    def verify_user_account(token: str) -> str:
        """
        Verifies a user account using a JWT email verification token.
        This does not require an authenticated context.
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

        user_repository = UserRepository()
        user = user_repository.get_user_by_email(email)

        if user.status == UserAccountStatus.ACTIVE.name_value:
            return UserResponseMessages.INVALID_REQUEST_MESSAGE.value

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

    def user_login(self, user_credentials: UserLoginModel) -> TokenResponseModel:
        """
        Authenticate user and return JWT token.
        Raises AppError if authentication fails.
        """
        user = self.user_repository.get_user_by_email(
            user_credentials.email, hash_password(user_credentials.password)
        )
        if not user:
            raise AppError(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message=UserResponseMessages.INVALID_CREDENTIALS.value,
            )
        return JWTManager().sign_jwt(user)

    def create_user(
        self, user_credentials: UserLoginModel, user_data: UserCreateModel
    ) -> UserReadModel:
        """
        Create a new user with the provided credentials and data.
        Raises AppError if user already exists or creation fails.
        """
        data = {
            "first_name": user_data.first_name,
            "last_name": user_data.last_name,
            "email": user_credentials.email,
            "phone_number": user_data.phone_number,
            "password": hash_password(user_credentials.password),
        }
        user = self.user_repository.create_user(data)
        self.context.user = user  # update context after creation
        self.send_verification_email(mode="create")
        return user

    def get_user_companies(self, params: CompanyQueryParams):
        """ Retrieve companies associated with the user. """
        return self.company_repository.get_user_companies(
            user_id=self.context.user.id, params=params
        )

    def get_user(
        self,
        user_id: Optional[int] = None,
        user_email: Optional[str] = None,
    ) -> UserReadModel:
        """
        Retrieve user details by ID or email.
        Raises AppError if user not found.
        """
        if user_id:
            return self.user_repository.get_user_by_id(user_id)
        elif user_email:
            return self.user_repository.get_user_by_email(user_email)
        else:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=UserResponseMessages.USER_NOT_FOUND.value,
            )

    def update_user(self, user_id: int, user_data: UserUpdateModel) -> UserReadModel:
        """
        Update user details with the provided data.
        Raises AppError if update fails or no data provided.
        """
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
        return self.user_repository.update_user(user_id, data)
