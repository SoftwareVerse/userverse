# tests/conftest.py
import os
import json
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import create_app
from app.utils.config.loader import ConfigLoader
from app.database.session_manager import DatabaseSessionManager
from app.database.user import User
from tests.utils.basic_auth import get_basic_auth_header

TEST_DATA_BASE_PATH = "tests/data/http/"

@pytest.fixture(scope="session")
def client():
    os.environ["ENV"] = "testing"
    # os.environ["DATABASE_URL"] = "sqlite:///:memory:"  # Use a test database URL

    # Load default test config from the loader (optional override)
    default_config = ConfigLoader(environment="testing").get_config()

    # Patch loader to always return the test config when app starts
    with patch.object(ConfigLoader, "get_config", return_value=default_config):
        app = create_app()
        with TestClient(app) as test_client:
            yield test_client


@pytest.fixture(scope="session")
def test_user_data():
    """Fixture to load test user data."""
    with open(f"{TEST_DATA_BASE_PATH}user.json") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def test_company_data():
    """Fixture to load test company data."""
    with open(f"{TEST_DATA_BASE_PATH}company.json") as f:
        return json.load(f)


@pytest.fixture
def get_user_two_otp(test_user_data):
    """Get OTP from user metadata."""
    user = test_user_data["user_two"]
    db = DatabaseSessionManager()
    session = db.session_object()
    user_row = session.query(User).filter_by(email=user["email"].lower()).first()
    if user_row:
        return user_row.primary_meta_data.get("password_reset", {}).get(
            "password_reset_token"
        )
    return None


@pytest.fixture
def login_token(client, test_user_data):
    """Login user_one and return access token."""
    user = test_user_data["user_one"]
    response = client.patch(
        "/user/login",
        headers=get_basic_auth_header(user["email"], user["password"]),
    )
    assert response.status_code in [200, 201, 202]
    return response.json()["data"]["access_token"]


@pytest.fixture
def login_token_user_two(client, test_user_data):
    """Login user_two and return access token."""
    user = test_user_data["user_two"]
    response = client.patch(
        "/user/login",
        headers=get_basic_auth_header(user["email"], user["password"]),
    )
    assert response.status_code in [200, 201, 202]
    return response.json()["data"]["access_token"]
