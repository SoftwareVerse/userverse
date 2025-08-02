from fastapi import status

# utils
from app.utils.app_error import AppError

# database
from app.database.session_manager import DatabaseSessionManager
from app.database.user import User

# models
from app.models.user.account_status import UserAccountStatus
from app.models.user.user import UserReadModel
from app.models.user.response_messages import UserResponseMessages
from app.utils.hash_password import verify_password


class UserRepository:
    def __init__(self):
        self.db_manager = DatabaseSessionManager()

    def get_user_by_id(self, user_id) -> UserReadModel:
        with self.db_manager.session_object() as session:
            user = User.get_by_id(session, user_id)
            if not user:
                raise AppError(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=UserResponseMessages.USER_NOT_FOUND.value,
                )
            return UserReadModel(
                id=user.get("id"),
                first_name=user.get("first_name"),
                last_name=user.get("last_name"),
                email=user.get("email"),
                phone_number=user.get("phone_number"),
                status=user.get("primary_meta_data", {}).get("status"),
                is_superuser=user.get("is_superuser"),
            )

    def get_user_by_email(self, user_email, password: str = None) -> UserReadModel:
        with self.db_manager.session_object() as session:
            user = session.query(User).filter(User.email == user_email).first()
            if not user:
                raise AppError(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=UserResponseMessages.USER_NOT_FOUND.value,
                )

            if password and verify_password(password, user.password):  # noqa: F821
                raise AppError(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    message=UserResponseMessages.INVALID_CREDENTIALS.value,
                )

            return UserReadModel(
                id=user.id,
                first_name=user.first_name,
                last_name=user.last_name,
                email=user.email,
                phone_number=user.phone_number,
                status=user.primary_meta_data.get("status"),
                is_superuser=user.is_superuser,
            )

    def create_user(self, data: dict) -> UserReadModel:
        with self.db_manager.session_object() as session:
            user = User.create(session, **data)
            if not user:
                raise AppError(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message=UserResponseMessages.USER_CREATION_FAILED.value,
                )

            self.update_user_status(
                user_id=user.get("id"),
                account_status=UserAccountStatus.AWAITING_VERIFICATION.name_value,
            )
            
            return UserReadModel(
                id=user.get("id"),
                first_name=user.get("first_name"),
                last_name=user.get("last_name"),
                email=user.get("email"),
                phone_number=user.get("phone_number"),
                status=UserAccountStatus.AWAITING_VERIFICATION.name_value,
                is_superuser=user.get("is_superuser"),
            )

    def update_user(self, user_id: int, data: dict):
        with self.db_manager.session_object() as session:
            user = User.update(session, record_id=user_id, **data)
            if not user:
                raise AppError(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message=UserResponseMessages.USER_UPDATE_FAILED.value,
                )
            return UserReadModel(
                id=user.get("id"),
                first_name=user.get("first_name"),
                last_name=user.get("last_name"),
                email=user.get("email"),
                phone_number=user.get("phone_number"),
                is_superuser=user.get("is_superuser"),
                status=user.get("primary_meta_data", {}).get("status"),
            )

    def update_user_status(self, user_id: int, account_status: str):
        with self.db_manager.session_object() as session:
            user = User.update_json_field(
                session=session,
                record_id=user_id,
                column_name="primary_meta_data",
                key="status",
                value=account_status,
            )
            if not user:
                raise AppError(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message=UserResponseMessages.USER_ACCOUNT_STATUS_UPDATE_FAILED.value,
                )
            return UserReadModel(
                id=user.get("id"),
                first_name=user.get("first_name"),
                last_name=user.get("last_name"),
                email=user.get("email"),
                phone_number=user.get("phone_number"),
                is_superuser=user.get("is_superuser"),
                status=account_status,
            )

    def delete_user(self, user_id):
        raise NotImplementedError("Delete user method not implemented")
