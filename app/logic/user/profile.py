from typing import Optional
from app.utils.shared_context import SharedContext
from app.repository.user import UserRepository
from app.logic.company.repository.company import CompanyRepository
from app.models.company.company import CompanyQueryParamsModel
from app.models.user.user import UserUpdateModel, UserReadModel
from app.utils.hash_password import hash_password
from app.utils.app_error import AppError
from app.models.user.response_messages import UserResponseMessages


class UserProfileService:
    """
    Service for managing user profiles.
    This service provides methods to get and update user profile information.
    It requires a SharedContext to access the user and database session.
    """

    def __init__(self, context: SharedContext):
        self.context = context
        self.user_repository = UserRepository()
        self.company_repository = CompanyRepository()

    def get_user(
        self, user_id: Optional[int] = None, user_email: Optional[str] = None
    ) -> UserReadModel:
        """
        Get user profile information.
        This method retrieves user details based on either user ID or email.
        If both are provided, user ID takes precedence.
        """
        if user_id:
            return self.user_repository.get_user_by_id(user_id)
        elif user_email:
            return self.user_repository.get_user_by_email(user_email)
        raise AppError(
            status_code=400,
            message=UserResponseMessages.USER_NOT_FOUND.value,
        )

    def update_user(self, user_id: int, user_data: UserUpdateModel) -> UserReadModel:
        """
        Update user profile information.
        This method allows updating user details such as name, phone number, and password.
        It requires the user ID to identify which user to update.
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
                status_code=400,
                message=UserResponseMessages.INVALID_REQUEST_MESSAGE.value,
            )
        return self.user_repository.update_user(user_id, data)

    def get_user_companies(self, params: CompanyQueryParamsModel):
        """
        Get companies associated with the user.
        This method retrieves a list of companies that the user is associated with.
        It requires the user ID from the context to filter the companies.
        """
        return self.company_repository.get_user_companies(
            user_id=self.context.user.id, params=params
        )
