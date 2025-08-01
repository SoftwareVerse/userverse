from fastapi import status

# utils
from app.logic.company.repository.company import CompanyRepository
from app.logic.mailer import MailService
from app.models.company.company import CompanyQueryParams
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
    ACCOUNT_REGISTRATION_TEMPLATE = "user_registration.html"
    ACCOUNT_REGISTRATION_SUBJECT = "User Account Registration"

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
        # TODO: User verification functionality
        verification_link = "https://github.com/SoftwareVerse"
        # send email
        MailService.send_template_email(
            to=user.email,
            subject=cls.ACCOUNT_REGISTRATION_SUBJECT,
            template_name=cls.ACCOUNT_REGISTRATION_TEMPLATE,
            context={
                "template_name": cls.ACCOUNT_REGISTRATION_SUBJECT,
                "user_name": (user.first_name or "") + " " + (user.last_name or ""),
                "verification_link": verification_link,
            },
        )

        return user

    @staticmethod
    def get_user_companies(
        params: CompanyQueryParams,
        user: UserReadModel,
    ):
        company_repository = CompanyRepository()
        return company_repository.get_user_companies(user_id=user.id, params=params)

    @staticmethod
    def get_user(user_id: int = None, user_email: str = None) -> UserReadModel:
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
