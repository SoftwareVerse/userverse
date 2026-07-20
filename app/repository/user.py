from fastapi import status
from sqlalchemy.exc import IntegrityError

from app.models.user.account_status import UserAccountStatus
from app.models.user.response_messages import UserResponseMessages
from app.models.user.user import UserReadModel
from app.repository.base import BaseSQLRepository
from app.repository.database.tables import User
from app.utils.app_error import AppError
from app.utils.hash_password import UnknownHashError, hash_password, verify_password


class UserRepository(BaseSQLRepository[User]):
    model = User
    REFRESH_TOKEN_VERSION_KEY = "refresh_token_version"

    def _active_user_query(self):
        return self._base_query().filter(User._closed_at.is_(None))

    @staticmethod
    def _to_read_model(
        user: User, *, status_override: str | None = None
    ) -> UserReadModel:
        metadata = user.primary_meta_data or {}
        return UserReadModel(
            id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
            phone_number=user.phone_number,
            status=status_override or metadata.get("status"),
            is_superuser=user.is_superuser,
        )

    def get_user_by_id(self, user_id: int) -> UserReadModel:
        try:
            user = self._active_user_query().filter(User.id == user_id).one_or_none()
            if user is None:
                raise AppError(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=UserResponseMessages.USER_NOT_FOUND.value,
                )
        except AppError:
            raise
        except Exception as exc:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                message=UserResponseMessages.USER_NOT_FOUND.value,
            ) from exc
        return self._to_read_model(user)

    def get_user_by_email(
        self, user_email: str, password: str | None = None
    ) -> UserReadModel:
        user = self._active_user_query().filter(User.email == user_email).first()
        if not user:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                message=UserResponseMessages.USER_NOT_FOUND.value,
            )

        if password is not None:
            try:
                is_valid = verify_password(password, user.password)
            except UnknownHashError:
                is_valid = password == user.password
                if is_valid:
                    user.password = hash_password(password)
                    self.db_session.commit()
                    self.db_session.refresh(user)

            if not is_valid:
                raise AppError(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    message=UserResponseMessages.INVALID_CREDENTIALS.value,
                )

        return self._to_read_model(user)

    def get_user_record_by_email(self, user_email: str) -> User | None:
        return self._active_user_query().filter(User.email == user_email).first()

    def create_user(
        self,
        data: dict,
        *,
        account_status: str = UserAccountStatus.AWAITING_VERIFICATION.name_value,
    ) -> UserReadModel:
        existing_user = (
            self._active_user_query().filter(User.email == data["email"]).first()
        )
        if existing_user:
            raise AppError(
                status_code=status.HTTP_409_CONFLICT,
                message=UserResponseMessages.USER_ALREADY_EXISTS.value,
            )

        try:
            user = self.create(**data)
        except IntegrityError as exc:
            self.db_session.rollback()
            if "UNIQUE constraint failed: user.email" in str(exc):
                raise AppError(
                    status_code=status.HTTP_409_CONFLICT,
                    message=UserResponseMessages.USER_ALREADY_EXISTS.value,
                ) from exc
            raise

        self.update_user_status(user_id=user.id, account_status=account_status)
        self.db_session.refresh(user)
        return self._to_read_model(user, status_override=account_status)

    def update_user(self, user_id: int, data: dict) -> UserReadModel:
        user = self._active_user_query().filter(User.id == user_id).one_or_none()
        if not user:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=UserResponseMessages.USER_UPDATE_FAILED.value,
            )
        updated = self.update(user, **data)
        return self._to_read_model(updated)

    def update_user_status(self, user_id: int, account_status: str) -> UserReadModel:
        user = self._active_user_query().filter(User.id == user_id).one_or_none()
        if not user:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=UserResponseMessages.USER_ACCOUNT_STATUS_UPDATE_FAILED.value,
            )
        updated = self.update_json_field(
            user,
            column_name="primary_meta_data",
            key="status",
            value=account_status,
        )
        return self._to_read_model(updated, status_override=account_status)

    def get_refresh_token_version(self, user_id: int) -> int:
        user = self._active_user_query().filter(User.id == user_id).first()
        if not user:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                message=UserResponseMessages.USER_NOT_FOUND.value,
            )

        metadata = user.primary_meta_data or {}
        refresh_token_version = metadata.get(self.REFRESH_TOKEN_VERSION_KEY, 0)
        try:
            return int(refresh_token_version)
        except (TypeError, ValueError):
            return 0

    def increment_refresh_token_version(self, user_id: int) -> int:
        user = self._active_user_query().filter(User.id == user_id).first()
        if not user:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                message=UserResponseMessages.USER_NOT_FOUND.value,
            )
        next_version = self.get_refresh_token_version(user_id) + 1
        updated_user = self.update_json_field(
            user,
            column_name="primary_meta_data",
            key=self.REFRESH_TOKEN_VERSION_KEY,
            value=next_version,
        )
        return int(
            updated_user.primary_meta_data.get(
                self.REFRESH_TOKEN_VERSION_KEY, next_version
            )
        )

    def delete_user(self, user_id: int):
        user = self._active_user_query().filter(User.id == user_id).one_or_none()
        if not user:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                message=UserResponseMessages.USER_NOT_FOUND.value,
            )
        self.soft_delete(user)
