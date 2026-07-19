from datetime import datetime, timedelta, timezone

from fastapi import status
from sqlalchemy.orm import Session

from app.models.user.response_messages import UserResponseMessages
from app.repository.base import BaseSQLRepository
from app.repository.database.tables import User
from app.utils.app_error import AppError


class UserPasswordRepository(BaseSQLRepository[User]):
    model = User

    def __init__(self, session: Session):
        super().__init__(session)

    def _get_user(self, user_email: str) -> User:
        user = self._base_query().filter(User.email == user_email).first()
        if not user:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                message=UserResponseMessages.USER_NOT_FOUND.value,
            )
        return user

    def update_password_reset_token(self, user_email: str, token: str) -> None:
        user = self._get_user(user_email)
        self.update_json_field(
            user,
            column_name="primary_meta_data",
            key="password_reset",
            value={
                "password_reset_token": token,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        )

    def verify_password_reset_token(self, user_email: str, token: str) -> bool:
        user = self._get_user(user_email)
        password_reset_data = (user.primary_meta_data or {}).get("password_reset", {})
        if password_reset_data.get("password_reset_token") != token:
            return False

        created_at = password_reset_data.get("created_at")
        if not created_at:
            return False

        return (datetime.fromisoformat(created_at) + timedelta(hours=1)) > datetime.now(timezone.utc)

    def update_password(self, user_email: str, new_password: str) -> None:
        user = self._get_user(user_email)
        user.password = new_password
        self.db_session.commit()
        self.db_session.refresh(user)
