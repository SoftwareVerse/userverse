from datetime import datetime, timedelta, timezone

from fastapi import status
from sqlalchemy.orm import Session

from app.models.user.password import PasswordResetMethod
from app.models.user.response_messages import UserResponseMessages
from app.repository.base import BaseSQLRepository
from app.repository.database.tables import User
from app.utils.app_error import AppError
from app.utils.hash_password import hash_password


class UserPasswordRepository(BaseSQLRepository[User]):
    model = User

    def __init__(self, session: Session):
        super().__init__(session)

    @staticmethod
    def _build_password_reset_record(
        *,
        method: PasswordResetMethod,
        token: str,
        expires_in: timedelta,
    ) -> dict[str, str]:
        created_at = datetime.now(timezone.utc)
        expires_at = created_at + expires_in
        return {
            "method": method.value,
            "token": token,
            "created_at": created_at.isoformat(),
            "expires_at": expires_at.isoformat(),
        }

    def _get_user(self, user_email: str) -> User:
        user = self._base_query().filter(User.email == user_email).first()
        if not user:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                message=UserResponseMessages.USER_NOT_FOUND.value,
            )
        return user

    def create_password_reset_record(
        self,
        user_email: str,
        *,
        method: PasswordResetMethod,
        token: str,
        expires_in: timedelta,
    ) -> None:
        user = self._get_user(user_email)
        self.update_json_field(
            user,
            column_name="primary_meta_data",
            key="password_reset",
            value=self._build_password_reset_record(
                method=method,
                token=token,
                expires_in=expires_in,
            ),
        )

    def verify_password_reset_token(
        self,
        user_email: str,
        *,
        method: PasswordResetMethod,
        token: str,
    ) -> bool:
        user = self._get_user(user_email)
        password_reset_data = (user.primary_meta_data or {}).get("password_reset", {})
        if password_reset_data.get("method") != method.value:
            return False

        if password_reset_data.get("token") != token:
            return False

        expires_at = password_reset_data.get("expires_at")
        if not expires_at:
            return False

        return datetime.fromisoformat(expires_at) > datetime.now(timezone.utc)

    def update_password(self, user_email: str, new_password: str) -> None:
        user = self._get_user(user_email)
        user.password = hash_password(new_password)
        self.clear_password_reset_record(user)
        self.db_session.commit()
        self.db_session.refresh(user)

    def clear_password_reset_record(self, user: User) -> None:
        password_reset_data = (user.primary_meta_data or {}).copy()
        password_reset_data.pop("password_reset", None)
        user.primary_meta_data = password_reset_data
