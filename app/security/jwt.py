import jwt
from datetime import datetime, timedelta, timezone
from fastapi import status, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# app imports
from app.configs import get_settings
from app.models.security_messages import SecurityResponseMessages
from app.models.user.user import TokenResponseModel, UserReadModel
from app.utils.app_error import AppError

http_bearer = HTTPBearer()


class JWTManager:
    """
    JWT Manager for handling JWT operations like signing, decoding, and refreshing tokens.
    This class is responsible for creating and validating JWT tokens used in the application.
    """

    def __init__(self):
        settings = get_settings()
        self.JWT_SECRET = settings.jwt.secret
        self.JWT_ALGORITHM = settings.jwt.algorithm
        self.SESSION_TIMEOUT = int(settings.jwt.timeout)
        self.REFRESH_TIMEOUT = int(settings.jwt.refresh_timeout)

    def sign_jwt(
        self, user: UserReadModel, *, refresh_token_version: int = 0
    ) -> TokenResponseModel:
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
            "refresh_token_version": refresh_token_version,
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

    def _decode_token_payload(self, token: str, *, expected_type: str) -> dict:
        try:
            decoded = jwt.decode(
                token, self.JWT_SECRET, algorithms=[self.JWT_ALGORITHM]
            )
            token_type = decoded.get("type")
            if token_type != expected_type:
                raise AppError(
                    status_code=status.HTTP_403_FORBIDDEN,
                    message=SecurityResponseMessages.INVALID_TOKEN.value
                    + f" for {expected_type} token",
                )

            user = decoded.get("user")
            if not user:
                raise AppError(
                    status_code=status.HTTP_403_FORBIDDEN,
                    message=SecurityResponseMessages.MISSING_USER_DATA.value,
                )
            return decoded

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

    def decode_token(self, token: str) -> UserReadModel:
        """
        Decode a JWT access token and return the user data.
        Raises AppError if the token is invalid or expired.
        """
        decoded = self._decode_token_payload(token, expected_type="access")
        return UserReadModel(**decoded["user"])

    def decode_refresh_token(self, token: str) -> tuple[UserReadModel, int]:
        decoded = self._decode_token_payload(token, expected_type="refresh")
        refresh_token_version = decoded.get("refresh_token_version", 0)
        try:
            normalized_version = int(refresh_token_version)
        except (TypeError, ValueError):
            normalized_version = 0

        return UserReadModel(**decoded["user"]), normalized_version

    def refresh_token(
        self,
        refresh_token: str,
        *,
        user: UserReadModel,
        refresh_token_version: int,
    ) -> TokenResponseModel:
        token_user, token_version = self.decode_refresh_token(refresh_token)
        if token_user.id != user.id or token_version != refresh_token_version:
            raise AppError(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message=SecurityResponseMessages.INVALID_TOKEN.value,
            )

        return self.sign_jwt(user, refresh_token_version=refresh_token_version)


async def get_current_user_from_jwt_token(
    credentials: HTTPAuthorizationCredentials = Depends(http_bearer),
) -> UserReadModel:
    """
    Get the current user from the JWT token in the Authorization header.
    Raises AppError if the token is missing or invalid.
    """
    authorization = credentials.credentials if credentials else None

    if authorization is None:
        raise AppError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            message=SecurityResponseMessages.INVALID_REQUEST.value,
            error=SecurityResponseMessages.MISSING_AUTHORIZATION_HEADER.value,
        )

    try:
        current_user = JWTManager().decode_token(authorization)
    except AppError:
        raise
    except Exception as e:
        raise AppError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            message=SecurityResponseMessages.INVALID_REQUEST.value,
            error=str(e),
        ) from e

    return current_user
