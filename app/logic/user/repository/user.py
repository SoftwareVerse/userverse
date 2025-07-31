from fastapi import status

# utils
from app.utils.app_error import AppError

# database
from app.database.session_manager import DatabaseSessionManager
from app.database.user import User

# models
from app.models.user.user import UserRead
from app.models.user.response_messages import UserResponseMessages


class UserRepository:
    def __init__(self):
        self.db_manager = DatabaseSessionManager()

    def get_user_by_id(self, user_id) -> UserRead:
        with self.db_manager.session_object() as session:
            user = User.get_by_id(session, user_id)
            if not user:
                raise AppError(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=UserResponseMessages.USER_NOT_FOUND.value,
                )
            return UserRead(
                id=user.get("id"),
                first_name=user.get("first_name"),
                last_name=user.get("last_name"),
                email=user.get("email"),
                phone_number=user.get("phone_number"),
            )

    def get_user_by_email(self, user_email, password: str = None) -> UserRead:
        with self.db_manager.session_object() as session:
            user = session.query(User).filter(User.email == user_email).first()
            if not user:
                raise AppError(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=UserResponseMessages.USER_NOT_FOUND.value,
                )

            if password and user.password != password:
                raise AppError(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    message=UserResponseMessages.INVALID_CREDENTIALS.value,
                )

            return UserRead(
                id=user.id,
                first_name=user.first_name,
                last_name=user.last_name,
                email=user.email,
                phone_number=user.phone_number,
            )

    def create_user(self, data: dict) -> UserRead:
        with self.db_manager.session_object() as session:
            user = User.create(session, **data)
            if not user:
                raise AppError(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message=UserResponseMessages.USER_CREATION_FAILED.value,
                )
            return UserRead(
                id=user.get("id"),
                first_name=user.get("first_name"),
                last_name=user.get("last_name"),
                email=user.get("email"),
                phone_number=user.get("phone_number"),
            )

    def update_user(self, user_id: int, data: dict):
        with self.db_manager.session_object() as session:
            user = User.update(session, record_id=user_id, **data)
            if not user:
                raise AppError(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message=UserResponseMessages.USER_UPDATE_FAILED.value,
                )
            return UserRead(
                id=user.get("id"),
                first_name=user.get("first_name"),
                last_name=user.get("last_name"),
                email=user.get("email"),
                phone_number=user.get("phone_number"),
            )

    def delete_user(self, user_id):
        raise NotImplementedError("Delete user method not implemented")
