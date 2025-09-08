import jwt
import traceback
from datetime import datetime, timedelta, timezone
from fastapi import status, Security
from fastapi.security import APIKeyHeader

# app imports
from app.utils.config.loader import ConfigLoader
from app.models.security_messages import SecurityResponseMessages
from app.models.user.user import TokenResponseModel, UserReadModel
from app.utils.app_error import AppError


class JWTManager:
    """
    JWT Manager for handling JWT operations like signing, decoding, and refreshing tokens.
    This class is responsible for creating and validating JWT tokens used in the application.
    """

    def __init__(self):
        # load configs
        loader = ConfigLoader()
        configs = loader.get_config()
        jwt_config = configs.get("jwt", {})
        self.JWT_SECRET = jwt_config.get("SECRET", "secret1234")
        self.JWT_ALGORITHM = jwt_config.get("ALGORITHM", "HS256")
        self.SESSION_TIMEOUT = int(jwt_config.get("IMEOUT", 15))
        self.REFRESH_TIMEOUT = int(jwt_config.get("REFRESH_TIMEOUT", 60))

    def sign_jwt(self, user: UserReadModel) -> TokenResponseModel:
        """Sign a JWT token with user data and return the token response model."""
        now = datetime.now(timezone.utc)
        access_expire = now + timedelta(minutes=self.SESSION_TIMEOUT)
        refresh_expire = now + timedelta(minutes=self.REFRESH_TIMEOUT)

        access_payload = {
            "user": user.model_dump(),
            "type": "access",
            "exp": access_expire,
        }

        refresh_payload = {
            "user": user.model_dump(),
            "type": "refresh",
            "exp": refresh_expire,
        }

        access_token = jwt.encode(
            payload=access_payload,
            key=self.JWT_SECRET,
            algorithm=self.JWT_ALGORITHM,
        )
        refresh_token = jwt.encode(
            payload=refresh_payload,
            key=self.JWT_SECRET,
            algorithm=self.JWT_ALGORITHM,
        )

        return TokenResponseModel(
            access_token=access_token,
            access_token_expiration=access_expire.strftime("%Y-%m-%d %H:%M:%S"),
            refresh_token=refresh_token,
            refresh_token_expiration=refresh_expire.strftime("%Y-%m-%d %H:%M:%S"),
            token_type="bearer",
        )

    def sign_payload(self, payload: dict, expires_delta: timedelta) -> str:
        """Sign a payload with JWT and return the token."""
        payload = payload.copy()
        payload["exp"] = datetime.now(timezone.utc) + expires_delta
        return jwt.encode(payload, self.JWT_SECRET, algorithm=self.JWT_ALGORITHM)

    def decode_verification_token(self, token: str) -> dict:
        """
        Decode a JWT verification token.
        Raises AppError if the token is invalid or expired.
        """
        try:
            decoded = jwt.decode(
                token, self.JWT_SECRET, algorithms=[self.JWT_ALGORITHM]
            )
            if decoded.get("type") != "verification":
                raise AppError(
                    status_code=status.HTTP_403_FORBIDDEN,
                    message=SecurityResponseMessages.INVALID_TOKEN.value
                    + " for verification",
                )
            return decoded
        except jwt.ExpiredSignatureError as exc:
            raise AppError(
                status_code=status.HTTP_403_FORBIDDEN,
                message=SecurityResponseMessages.EXPIRED_TOKEN.value,
            ) from exc
        except Exception as exc:
            raise AppError(
                status_code=status.HTTP_403_FORBIDDEN,
                message=SecurityResponseMessages.INVALID_TOKEN.value,
            ) from exc

    def decode_token(self, token: str) -> UserReadModel:
        """
        Decode a JWT token and return the user data.
        Raises AppError if the token is invalid or expired.
        """
        try:
            decoded = jwt.decode(
                token, self.JWT_SECRET, algorithms=[self.JWT_ALGORITHM]
            )
            user = decoded.get("user")
            if not user:
                raise AppError(
                    status_code=status.HTTP_403_FORBIDDEN,
                    message=SecurityResponseMessages.MISSING_USER_DATA.value,
                )
            if decoded.get("type") != "access":
                raise AppError(
                    status_code=status.HTTP_403_FORBIDDEN,
                    message=SecurityResponseMessages.INVALID_TOKEN.value
                    + " for access token",
                )
            return UserReadModel(**user)

        except jwt.ExpiredSignatureError as e:
            raise AppError(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message=SecurityResponseMessages.EXPIRED_TOKEN.value,
            ) from e
        except jwt.InvalidTokenError as e:
            raise AppError(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message=SecurityResponseMessages.INVALID_TOKEN.value,
            ) from e
        except AppError:
            raise  # ⬅️ This ensures your own exceptions aren't re-wrapped
        except Exception as e:
            raise AppError(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=SecurityResponseMessages.ERROR_DECODING.value,
                error=str(e),
            ) from e

    def refresh_token(self, refresh_token: str) -> TokenResponseModel:
        try:
            decoded = self.decode_token(refresh_token)
            if decoded.get("type") != "refresh":
                raise AppError(
                    status_code=status.HTTP_403_FORBIDDEN,
                    message=SecurityResponseMessages.INVALID_TOKEN.value
                    + " for refresh token",
                )

            user = decoded.get("user")
            if not user:
                raise AppError(
                    status_code=status.HTTP_403_FORBIDDEN,
                    message=SecurityResponseMessages.MISSING_USER_DATA.value,
                )

            return self.signJWT(user)

        except Exception as e:
            traceback.print_exc()
            raise AppError(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=str(e),
            ) from e


async def get_current_user_from_jwt_token(
    authorization: str = Security(APIKeyHeader(name="Authorization")),
) -> UserReadModel:
    """
    Get the current user from the JWT token in the Authorization header.
    Raises AppError if the token is missing or invalid.
    """

    if authorization is None:
        raise AppError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            message=SecurityResponseMessages.INVALID_REQUEST.value,
            error=SecurityResponseMessages.MISSING_AUTHORIZATION_HEADER.value,
        )

    try:
        auth_type, TOKEN = authorization.split(" ")
        if auth_type.strip().lower() != "bearer":
            raise AppError(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message=SecurityResponseMessages.INVALID_REQUEST.value,
                error=SecurityResponseMessages.MISSING_AUTHORIZATION_HEADER.value,
            )
    except Exception as e:
        raise AppError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            message=SecurityResponseMessages.INVALID_REQUEST.value,
            error=str(e),
        ) from e

    current_user = JWTManager().decode_token(TOKEN)

    return current_user
