import pytest
from datetime import datetime, timedelta, timezone
from fastapi import status
import jwt

from app.models.user.user import UserReadModel
from app.models.security_messages import SecurityResponseMessages
from app.security.jwt import JWTManager
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
