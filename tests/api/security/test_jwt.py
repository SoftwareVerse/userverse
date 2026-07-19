import asyncio
import pytest
from datetime import datetime, timedelta, timezone
from fastapi import status
from fastapi.security import HTTPAuthorizationCredentials
import jwt

from app.models.user.user import UserReadModel
from app.models.security_messages import SecurityResponseMessages
from app.api.security.jwt import JWTManager, get_current_user_from_jwt_token
from app.utils.app_error import AppError

# Sample user
sample_user = UserReadModel(
    id=1,
    first_name="Test",
    last_name="User",
    email="test@example.com",
    phone_number="1234567890",
)


def test_sign_jwt_contains_access_and_refresh_tokens():
    jwt_manager = JWTManager()
    tokens = jwt_manager.sign_jwt(sample_user)

    assert tokens.access_token
    assert tokens.refresh_token
    assert "access_token_expiration" in tokens.model_dump()
    assert "refresh_token_expiration" in tokens.model_dump()


def test_decode_valid_access_token():
    jwt_manager = JWTManager()
    tokens = jwt_manager.sign_jwt(sample_user)
    user = jwt_manager.decode_token(tokens.access_token)
    assert user.email == sample_user.email


def test_decode_valid_refresh_token():
    jwt_manager = JWTManager()
    tokens = jwt_manager.sign_jwt(sample_user, refresh_token_version=3)
    user, refresh_token_version = jwt_manager.decode_refresh_token(tokens.refresh_token)

    assert user.email == sample_user.email
    assert refresh_token_version == 3


def test_decode_refresh_token_invalid_version_defaults_to_zero():
    jwt_manager = JWTManager()
    token = jwt.encode(
        {
            "user": sample_user.model_dump(),
            "type": "refresh",
            "refresh_token_version": "invalid",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        jwt_manager.JWT_SECRET,
        algorithm=jwt_manager.JWT_ALGORITHM,
    )

    user, refresh_token_version = jwt_manager.decode_refresh_token(token)

    assert user.email == sample_user.email
    assert refresh_token_version == 0


def test_decode_token_missing_user_data():
    jwt_manager = JWTManager()
    token = jwt.encode(
        {"type": "access", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        jwt_manager.JWT_SECRET,
        algorithm=jwt_manager.JWT_ALGORITHM,
    )
    with pytest.raises(AppError) as e:
        jwt_manager.decode_token(token)
    assert e.value.status_code == status.HTTP_403_FORBIDDEN


def test_decode_expired_token():
    jwt_manager = JWTManager()
    token = jwt.encode(
        {
            "user": sample_user.model_dump(),
            "type": "access",
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        },
        jwt_manager.JWT_SECRET,
        algorithm=jwt_manager.JWT_ALGORITHM,
    )
    with pytest.raises(AppError) as e:
        jwt_manager.decode_token(token)
    assert e.value.status_code == status.HTTP_401_UNAUTHORIZED


def test_decode_invalid_token_signature():
    jwt_manager = JWTManager()
    tokens = jwt_manager.sign_jwt(sample_user)
    tampered_token = tokens.access_token + "tamper"
    with pytest.raises(AppError) as e:
        jwt_manager.decode_token(tampered_token)
    assert e.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert e.value.detail["message"] == SecurityResponseMessages.INVALID_TOKEN.value


def test_decode_token_wraps_unexpected_decode_error(monkeypatch):
    monkeypatch.setattr(
        "app.api.security.jwt.jwt.decode", lambda *args, **kwargs: 1 / 0
    )
    jwt_manager = JWTManager()

    with pytest.raises(AppError) as e:
        jwt_manager.decode_token("signed-token")

    assert e.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert e.value.detail["message"] == SecurityResponseMessages.ERROR_DECODING.value
    assert "division by zero" in e.value.detail["error"]


def test_decode_refresh_token_rejects_access_token():
    jwt_manager = JWTManager()
    tokens = jwt_manager.sign_jwt(sample_user)

    with pytest.raises(AppError) as e:
        jwt_manager.decode_refresh_token(tokens.access_token)

    assert e.value.status_code == status.HTTP_403_FORBIDDEN
    assert (
        e.value.detail["message"]
        == SecurityResponseMessages.INVALID_TOKEN.value + " for refresh token"
    )


def test_refresh_token_returns_rotated_tokens():
    jwt_manager = JWTManager()
    tokens = jwt_manager.sign_jwt(sample_user, refresh_token_version=2)

    refreshed_tokens = jwt_manager.refresh_token(
        tokens.refresh_token,
        user=sample_user,
        refresh_token_version=2,
    )
    _, refresh_token_version = jwt_manager.decode_refresh_token(
        refreshed_tokens.refresh_token
    )

    assert refreshed_tokens.access_token
    assert refreshed_tokens.refresh_token
    assert refresh_token_version == 2


def test_refresh_token_rejects_revoked_version():
    jwt_manager = JWTManager()
    tokens = jwt_manager.sign_jwt(sample_user, refresh_token_version=1)

    with pytest.raises(AppError) as e:
        jwt_manager.refresh_token(
            tokens.refresh_token,
            user=sample_user,
            refresh_token_version=2,
        )

    assert e.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert e.value.detail["message"] == SecurityResponseMessages.INVALID_TOKEN.value


def test_decode_verification_token_success():
    jwt_manager = JWTManager()
    token = jwt_manager.sign_payload(
        {"sub": sample_user.email, "type": "verification"},
        expires_delta=timedelta(minutes=5),
    )

    decoded = jwt_manager.decode_verification_token(token)

    assert decoded["sub"] == sample_user.email
    assert decoded["type"] == "verification"


def test_decode_verification_token_rejects_wrong_type():
    jwt_manager = JWTManager()
    token = jwt_manager.sign_payload(
        {"sub": sample_user.email, "type": "access"},
        expires_delta=timedelta(minutes=5),
    )

    with pytest.raises(AppError) as e:
        jwt_manager.decode_verification_token(token)

    assert e.value.status_code == status.HTTP_403_FORBIDDEN
    assert e.value.detail["message"] == SecurityResponseMessages.INVALID_TOKEN.value


def test_decode_verification_token_rejects_expired_token():
    jwt_manager = JWTManager()
    token = jwt.encode(
        {
            "sub": sample_user.email,
            "type": "verification",
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        },
        jwt_manager.JWT_SECRET,
        algorithm=jwt_manager.JWT_ALGORITHM,
    )

    with pytest.raises(AppError) as e:
        jwt_manager.decode_verification_token(token)

    assert e.value.status_code == status.HTTP_403_FORBIDDEN
    assert e.value.detail["message"] == SecurityResponseMessages.EXPIRED_TOKEN.value


def test_get_current_user_from_jwt_token_rejects_missing_credentials():
    with pytest.raises(AppError) as e:
        asyncio.run(get_current_user_from_jwt_token(session=object(), credentials=None))

    assert e.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert e.value.detail["message"] == SecurityResponseMessages.INVALID_REQUEST.value
    assert (
        e.value.detail["error"]
        == SecurityResponseMessages.MISSING_AUTHORIZATION_HEADER.value
    )


def test_get_current_user_from_jwt_token_returns_decoded_user(monkeypatch):
    monkeypatch.setattr(
        "app.api.security.jwt.JWTManager.decode_token",
        lambda self, token: sample_user,
    )
    monkeypatch.setattr(
        "app.api.security.jwt.UserRepository.get_user_by_id",
        lambda self, user_id: sample_user.model_copy(update={"status": "Active"}),
    )
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer", credentials="signed-token"
    )

    current_user = asyncio.run(
        get_current_user_from_jwt_token(session=object(), credentials=credentials)
    )

    assert current_user.email == sample_user.email


def test_get_current_user_from_jwt_token_reraises_app_error(monkeypatch):
    expected_error = AppError(
        status_code=status.HTTP_401_UNAUTHORIZED,
        message=SecurityResponseMessages.INVALID_TOKEN.value,
        log_error=False,
    )

    def _raise(self, token):
        raise expected_error

    monkeypatch.setattr("app.api.security.jwt.JWTManager.decode_token", _raise)
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer", credentials="signed-token"
    )

    with pytest.raises(AppError) as e:
        asyncio.run(
            get_current_user_from_jwt_token(session=object(), credentials=credentials)
        )

    assert e.value is expected_error


def test_get_current_user_from_jwt_token_wraps_unexpected_error(monkeypatch):
    def _raise(self, token):
        raise RuntimeError("decode failed")

    monkeypatch.setattr("app.api.security.jwt.JWTManager.decode_token", _raise)
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer", credentials="signed-token"
    )

    with pytest.raises(AppError) as e:
        asyncio.run(
            get_current_user_from_jwt_token(session=object(), credentials=credentials)
        )

    assert e.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert e.value.detail["message"] == SecurityResponseMessages.INVALID_REQUEST.value
    assert e.value.detail["error"] == "decode failed"


def test_get_current_user_from_jwt_token_rejects_inactive_database_user(monkeypatch):
    monkeypatch.setattr(
        "app.api.security.jwt.JWTManager.decode_token",
        lambda self, token: sample_user,
    )
    inactive_user = sample_user.model_copy(update={"status": "Suspended"})
    monkeypatch.setattr(
        "app.api.security.jwt.UserRepository.get_user_by_id",
        lambda self, user_id: inactive_user,
    )
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer", credentials="signed-token"
    )

    with pytest.raises(AppError) as e:
        asyncio.run(
            get_current_user_from_jwt_token(session=object(), credentials=credentials)
        )

    assert e.value.status_code == status.HTTP_403_FORBIDDEN
