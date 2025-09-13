from fastapi import status
from datetime import datetime, timedelta, timezone

# utils
from app.utils.app_error import AppError

# database
from sqlalchemy.orm import Session
from app.database.user import User

# models
from app.models.user.response_messages import UserResponseMessages


class UserPasswordRepository:
    """
    This class handles user password management, including updating,
    verifying, resetting, and changing passwords.
    """

    def __init__(self, session: Session):
        self.session = session

    def update_password_reset_token(self, user_email: str, token: str) -> None:
        """
        Update the password reset token for a user.
        """
        session = self.session
        user = session.query(User).filter(User.email == user_email).first()
        if not user:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                message=UserResponseMessages.USER_NOT_FOUND.value,
            )

        user.update_json_field(
            session=session,
            record_id=user.id,
            column_name="primary_meta_data",
            key="password_reset",
            value={
                "password_reset_token": token,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        session.commit()

    def verify_password_reset_token(self, user_email: str, token: str) -> bool:
        """
        Verify the password reset token for a user.
        """
        session = self.session
        user = session.query(User).filter(User.email == user_email).first()
        if not user:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                message=UserResponseMessages.USER_NOT_FOUND.value,
            )

        # Check if the token is valid and not expired
        password_reset_data = user.primary_meta_data.get("password_reset", {})
        if password_reset_data.get("password_reset_token") == token and (
            datetime.fromisoformat(password_reset_data.get("created_at"))
            + timedelta(hours=1)
        ) > datetime.now(timezone.utc):
            return True

        return False

    def update_password(self, user_email: str, new_password: str) -> None:
        """
        Update the password for a user.
        """
        session = self.session
        user = session.query(User).filter(User.email == user_email).first()
        if not user:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                message=UserResponseMessages.USER_NOT_FOUND.value,
            )

        user.password = new_password
        session.commit()
        session.refresh(user)
