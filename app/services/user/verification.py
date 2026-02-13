from fastapi import status
from sqlalchemy.orm import Session
from app.repository.user import UserRepository
from app.security.jwt import JWTManager
from app.utils.app_error import AppError
from app.models.user.account_status import UserAccountStatus
from app.models.user.response_messages import UserResponseMessages


class UserVerificationService:
    """
    Service for handling user account verification via JWT tokens.
    This service does not require an authenticated context to run.
    """

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
