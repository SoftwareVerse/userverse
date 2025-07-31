from fastapi import Depends, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import ValidationError
from app.models.security_messages import SecurityResponseMessages
from app.utils.app_error import AppError
from app.models.user.user import UserLogin

security = HTTPBasic()


def get_basic_auth_credentials(credentials: HTTPBasicCredentials = Depends(security))-> UserLogin:
    try:
        email = credentials.username
        if not email:
            raise AppError(
                SecurityResponseMessages.INVALID_CREDENTIALS_MESSAGE.value,
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
        password = credentials.password
        if not password:
            raise AppError(
                SecurityResponseMessages.INVALID_CREDENTIALS_MESSAGE.value,
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        inputs = UserLogin(email=credentials.username, password=password)
        return inputs
    except ValidationError as e:
        raise AppError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            message=SecurityResponseMessages.INVALID_CREDENTIALS_MESSAGE.value,
            error=str(e),
        )
    except Exception as e:
        raise AppError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            message=SecurityResponseMessages.INVALID_CREDENTIALS_MESSAGE.value,
            error=str(e),
        )
