# tests/conftest.py
import os
import json
import logging
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import create_app
import app.database.session_manager as session_manager
from app.database.session_manager import DatabaseSessionManager
from app.database.user import User
from app.database.company import Company
from app.database.role import Role
from app.database.association_user_company import AssociationUserCompany
from app.models.user.account_status import UserAccountStatus
from tests.utils.basic_auth import get_basic_auth_header
from app.security.jwt import JWTManager
from datetime import timedelta

TEST_DATA_BASE_PATH = "tests/data/http/"


@pytest.fixture(scope="session", autouse=True)
def test_runtime_guards():
    noisy_loggers = ("httpx", "httpcore", "urllib3", "asyncio")
    previous_levels = {
        logger_name: logging.getLogger(logger_name).level
        for logger_name in noisy_loggers
    }

    for logger_name in noisy_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    with patch(
        "app.services.mailer.MailService.send_template_email", return_value=None
    ):
        yield

    for logger_name, level in previous_levels.items():
        logging.getLogger(logger_name).setLevel(level)


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """
    Setup a clean database for the test session.
    Forces the application to use a test-specific database file.
    """
    db_path = "./test.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    # Ensure any new DatabaseSessionManager instances use this DB.
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["ENV"] = "testing"

    default_db = DatabaseSessionManager()
    session_manager._default_db = default_db

    yield

    # Teardown
    default_db.engine.dispose()
    session_manager._default_db = None
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture(scope="session")
def client():
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


def _get_user_row(email: str):
    db = DatabaseSessionManager()
    session = db.session_object()
    try:
        return session.query(User).filter_by(email=email.lower()).first()
    finally:
        session.close()


def _get_company_row(email: str):
    db = DatabaseSessionManager()
    session = db.session_object()
    try:
        return session.query(Company).filter_by(email=email.lower()).first()
    finally:
        session.close()


def _get_role_row(company_id: int, name: str):
    db = DatabaseSessionManager()
    session = db.session_object()
    try:
        return (
            session.query(Role)
            .filter_by(company_id=company_id, name=name, _closed_at=None)
            .first()
        )
    finally:
        session.close()


def _get_link_row(company_id: int, user_id: int):
    db = DatabaseSessionManager()
    session = db.session_object()
    try:
        return (
            session.query(AssociationUserCompany)
            .filter_by(company_id=company_id, user_id=user_id, _closed_at=None)
            .first()
        )
    finally:
        session.close()


def _create_user_if_missing(client: TestClient, user: dict):
    if _get_user_row(user["email"]):
        return

    payload = {
        "first_name": user["first_name"],
        "last_name": user["last_name"],
        "phone_number": user["phone_number"],
    }
    response = client.post(
        "/user/create",
        json=payload,
        headers=get_basic_auth_header(user["email"], user["password"]),
    )
    assert response.status_code in [200, 201], response.text


def _login_user(client: TestClient, user: dict) -> str:
    response = client.patch(
        "/user/login",
        headers=get_basic_auth_header(user["email"], user["password"]),
    )
    assert response.status_code in [200, 201, 202], response.text
    return response.json()["data"]["access_token"]


def _create_company_if_missing(client: TestClient, token: str, company: dict):
    if _get_company_row(company["email"]):
        return

    payload = {
        **company,
        "address": {
            "street": "123 Main St",
            "city": "Johannesburg",
            "state": "Gauteng",
            "postal_code": "2000",
            "country": "South Africa",
        },
    }
    response = client.post(
        "/company",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code in [200, 201], response.text


def _create_role_if_missing(
    client: TestClient, *, company_id: int, token: str, role_payload: dict
):
    if _get_role_row(company_id, role_payload["name"]):
        return

    response = client.post(
        f"/company/{company_id}/role",
        json=role_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code in [200, 201], response.text


@pytest.fixture
def get_user_two_otp(test_user_data):
    """Get OTP from user metadata."""
    user = test_user_data["user_two"]
    db = DatabaseSessionManager()
    session = db.session_object()
    try:
        user_row = session.query(User).filter_by(email=user["email"].lower()).first()
        if user_row:
            return user_row.primary_meta_data.get("password_reset", {}).get(
                "password_reset_token"
            )
        return None
    finally:
        session.close()


@pytest.fixture(scope="session")
def seed_users(client, test_user_data):
    for key in ("user_one", "user_two", "user_three"):
        _create_user_if_missing(client, test_user_data[key])


@pytest.fixture(scope="session")
def seed_verified_users(client, seed_users, test_user_data):
    for key in ("user_one", "user_two", "user_three"):
        user = _get_user_row(test_user_data[key]["email"])
        status = (user.primary_meta_data or {}).get("status") if user else None
        if status != UserAccountStatus.ACTIVE.name_value:
            _verify_user_account(client, test_user_data[key]["email"])


@pytest.fixture(scope="session")
def login_token(client, seed_verified_users, test_user_data):
    """Login user_one and return access token."""
    return _login_user(client, test_user_data["user_one"])


@pytest.fixture(scope="session")
def login_token_user_two(client, seed_verified_users, test_user_data):
    """Login user_two and return access token."""
    return _login_user(client, test_user_data["user_two"])


def _verify_user_account(client: TestClient, email: str):
    token = JWTManager().sign_payload(
        {"sub": email, "type": "verification"}, expires_delta=timedelta(minutes=60)
    )
    response = client.get(f"/user/verify?token={token}")
    assert response.status_code in [200, 201]


@pytest.fixture
def verify_user_one_account(client, test_user_data):
    _verify_user_account(client, test_user_data["user_one"]["email"])


@pytest.fixture
def verify_user_two_account(client, test_user_data):
    _verify_user_account(client, test_user_data["user_two"]["email"])


@pytest.fixture
def verify_both_users(verify_user_one_account, verify_user_two_account):
    # Ensures both users verified before tests
    pass


@pytest.fixture(scope="session")
def seed_companies(client, test_company_data, login_token, login_token_user_two):
    _create_company_if_missing(client, login_token, test_company_data["company_one"])
    _create_company_if_missing(
        client, login_token_user_two, test_company_data["company_two"]
    )


@pytest.fixture(scope="session")
def seed_company_roles(
    client, seed_companies, test_company_data, login_token, login_token_user_two
):
    for role_payload in test_company_data["roles"].values():
        _create_role_if_missing(
            client,
            company_id=1,
            token=login_token,
            role_payload=role_payload,
        )
        _create_role_if_missing(
            client,
            company_id=2,
            token=login_token_user_two,
            role_payload=role_payload,
        )


@pytest.fixture(scope="session")
def seed_pagination_state(client):
    owner = {
        "first_name": "Pagy",
        "last_name": "Owner",
        "phone_number": "0333333333",
        "email": "pagination.owner@email.com",
        "password": "secureOwner",
    }
    _create_user_if_missing(client, owner)
    owner_row = _get_user_row(owner["email"])
    owner_status = (owner_row.primary_meta_data or {}).get("status")
    if owner_status != UserAccountStatus.ACTIVE.name_value:
        _verify_user_account(client, owner["email"])
    owner_token = _login_user(client, owner)

    companies = [
        {
            "email": "pagination.company.one@email.com",
            "name": "Pagination Company One",
            "description": "Dedicated pagination company one.",
            "industry": "Retail",
            "phone_number": "+27134567890",
        },
        {
            "email": "pagination.company.two@email.com",
            "name": "Pagination Company Two",
            "description": "Dedicated pagination company two.",
            "industry": "Logistics",
            "phone_number": "+27145678901",
        },
        {
            "email": "pagination.company.three@email.com",
            "name": "Pagination Company Three",
            "description": "Dedicated pagination company three.",
            "industry": "Energy",
            "phone_number": "+27156789012",
        },
        {
            "email": "pagination.company.four@email.com",
            "name": "Pagination Company Four",
            "description": "Dedicated pagination company four.",
            "industry": "Media",
            "phone_number": "+27167890123",
        },
    ]

    for company in companies:
        _create_company_if_missing(client, owner_token, company)

    role_company = _get_company_row("pagination.company.one@email.com")
    users_company = _get_company_row("pagination.company.two@email.com")
    user_companies = [
        _get_company_row("pagination.company.one@email.com"),
        _get_company_row("pagination.company.two@email.com"),
        _get_company_row("pagination.company.three@email.com"),
        _get_company_row("pagination.company.four@email.com"),
    ]

    for role_payload in (
        {"name": "User", "description": "Standard user role with limited access."},
        {
            "name": "Client",
            "description": "Client role with access to client features.",
        },
    ):
        _create_role_if_missing(
            client,
            company_id=role_company.id,
            token=owner_token,
            role_payload=role_payload,
        )

    extra_users = [
        {
            "first_name": "Alex",
            "last_name": "Page",
            "phone_number": "0111111111",
            "email": "pagination.user.one@email.com",
            "password": "secureFour",
        },
        {
            "first_name": "Taylor",
            "last_name": "Page",
            "phone_number": "0222222222",
            "email": "pagination.user.two@email.com",
            "password": "secureFive",
        },
        {
            "first_name": "Morgan",
            "last_name": "Page",
            "phone_number": "0444444444",
            "email": "pagination.user.three@email.com",
            "password": "secureSix",
        },
    ]

    for user in extra_users:
        _create_user_if_missing(client, user)
        user_row = _get_user_row(user["email"])
        if not _get_link_row(company_id=users_company.id, user_id=user_row.id):
            response = client.post(
                f"/company/{users_company.id}/users",
                json={"email": user["email"], "role": "Viewer"},
                headers={"Authorization": f"Bearer {owner_token}"},
            )
            assert response.status_code == 201, response.text

    return {
        "owner": owner,
        "owner_token": owner_token,
        "role_company_id": role_company.id,
        "users_company_id": users_company.id,
        "user_company_ids": [company.id for company in user_companies],
    }
