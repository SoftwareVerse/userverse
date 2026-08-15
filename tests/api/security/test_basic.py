# Unit tests
from fastapi import status
from fastapi.security import HTTPBasicCredentials
import pytest
from app.models.user.user import UserLoginModel

from app.api.security.basic_auth import get_basic_auth_credentials
from app.utils.app_error import AppError


def test_valid_credentials():
    credentials = HTTPBasicCredentials(
        username="user@example.com", password="securepass"
    )
    result = get_basic_auth_credentials(credentials)
    expected = UserLoginModel(email="user@example.com", password="securepass")
    assert isinstance(result, UserLoginModel)
    assert result.email == expected.email
    assert result.password == expected.password


def test_missing_username():
    credentials = HTTPBasicCredentials(username="", password="securepass")
    with pytest.raises(AppError) as e:
        get_basic_auth_credentials(credentials)
    assert e.value.status_code == status.HTTP_401_UNAUTHORIZED


def test_missing_password():
    credentials = HTTPBasicCredentials(username="user@example.com", password="")
    with pytest.raises(AppError) as e:
        get_basic_auth_credentials(credentials)
    assert e.value.status_code == status.HTTP_401_UNAUTHORIZED


def test_invalid_pydantic_input():
    credentials = HTTPBasicCredentials(username="not-an-email", password="securepass")
    with pytest.raises(AppError) as e:
        get_basic_auth_credentials(credentials)
    assert e.value.status_code == status.HTTP_401_UNAUTHORIZED


def test_unexpected_error_is_wrapped(monkeypatch):
    credentials = HTTPBasicCredentials(
        username="user@example.com", password="securepass"
    )

    def boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("app.api.security.basic_auth.UserLoginModel", boom)

    with pytest.raises(AppError) as exc_info:
        get_basic_auth_credentials(credentials)

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail["error"] == "boom"
