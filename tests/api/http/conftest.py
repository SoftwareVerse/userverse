# tests/conftest.py
import json
import logging
import os
import tempfile
from datetime import timedelta
from pathlib import Path
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from dotenv import dotenv_values
from unittest.mock import patch

import app.configs as app_configs
from app.api.security.jwt import JWTManager
from app.main import create_app
from app.models.company.roles import CompanyDefaultRoles
from app.models.user.account_status import UserAccountStatus
from app.models.user.user import UserReadModel
from app.configs import settings
from app.repository.database.session_manager import DatabaseSessionManager
from app.repository.database.tables import AssociationUserCompany, Company, Role, User
from app.repository.database.tables import CompanyRole
import app.repository.database.session_manager as session_manager
from app.utils.hash_password import hash_password
from tests.utils.basic_auth import get_basic_auth_header

TEST_DATA_BASE_PATH = "tests/data/http/"
BASE_URL = "http://testserver"
HTTP_TEST_SETTING_NAMES = (
    "DATABASE_URL",
    "ENV",
    "ENVIRONMENT",
    "TESTING",
    "DB_AUTO_CREATE",
    "FRONTEND_URL",
    "JWT_SECRET",
)


def pytest_addoption(parser):
    parser.addoption(
        "--http-env-file",
        action="store",
        default=None,
        help=(
            "Use the provided env file for HTTP tests instead of the default isolated "
            "temporary SQLite configuration."
        ),
    )


def _apply_runtime_settings(overrides: dict[str, str]) -> None:
    app_configs._resolve_settings.cache_clear()

    for name, value in overrides.items():
        os.environ[name] = value

    settings.DATABASE_URL = overrides["DATABASE_URL"]
    settings.ENVIRONMENT = overrides.get(
        "ENVIRONMENT", overrides.get("ENV", settings.ENVIRONMENT)
    )
    settings.TESTING = overrides["TESTING"].lower() == "true"
    settings.DB_AUTO_CREATE = overrides["DB_AUTO_CREATE"].lower() == "true"
    settings.FRONTEND_URL = overrides["FRONTEND_URL"]
    settings.JWT_SECRET = overrides["JWT_SECRET"]


def _build_default_http_test_settings(db_path: Path) -> dict[str, str]:
    return {
        "DATABASE_URL": f"sqlite:///{db_path}",
        "ENV": "testing",
        "ENVIRONMENT": "testing",
        "TESTING": "true",
        "DB_AUTO_CREATE": "true",
        "FRONTEND_URL": "https://frontend.example.com/reset-password",
        "JWT_SECRET": "testing-secret-key-with-at-least-32-bytes",
    }


def _load_http_test_env_file(env_file: str) -> dict[str, str]:
    env_path = Path(env_file).expanduser().resolve()
    if not env_path.exists():
        raise pytest.UsageError(f"--http-env-file not found: {env_path}")

    loaded = {
        key: str(value)
        for key, value in dotenv_values(env_path).items()
        if value is not None
    }
    if "DATABASE_URL" not in loaded:
        raise pytest.UsageError(f"--http-env-file must define DATABASE_URL: {env_path}")

    loaded.setdefault("ENV", loaded.get("ENVIRONMENT", "testing"))
    loaded.setdefault("ENVIRONMENT", loaded.get("ENV", "testing"))
    loaded.setdefault("TESTING", "true")
    loaded.setdefault("DB_AUTO_CREATE", "true")
    loaded.setdefault("FRONTEND_URL", "https://frontend.example.com/reset-password")
    loaded.setdefault("JWT_SECRET", "testing-secret-key-with-at-least-32-bytes")
    return loaded


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
def setup_database(pytestconfig):
    """
    Setup a clean database for the test session.
    By default this uses a test-specific database file.
    Passing --http-env-file uses that env file instead.
    """
    original_env = {name: os.environ.get(name) for name in HTTP_TEST_SETTING_NAMES}
    db_dir = Path(tempfile.mkdtemp(prefix="userverse-http-tests-"))
    db_path = db_dir / "test.db"
    env_file = pytestconfig.getoption("--http-env-file")
    runtime_settings = (
        _load_http_test_env_file(env_file)
        if env_file
        else _build_default_http_test_settings(db_path)
    )
    _apply_runtime_settings(runtime_settings)

    default_db = DatabaseSessionManager()
    session_manager._default_db = default_db

    yield

    default_db.engine.dispose()
    session_manager._default_db = None
    app_configs._resolve_settings.cache_clear()
    for setting_name in (
        "DATABASE_URL",
        "ENVIRONMENT",
        "TESTING",
        "DB_AUTO_CREATE",
        "FRONTEND_URL",
        "JWT_SECRET",
    ):
        try:
            delattr(settings, setting_name)
        except AttributeError:
            pass
    for name, original_value in original_env.items():
        if original_value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = original_value
    if not env_file and db_path.exists():
        db_path.unlink()
    if not env_file and db_dir.exists():
        db_dir.rmdir()


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url=BASE_URL) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def test_user_data():
    with open(f"{TEST_DATA_BASE_PATH}user.json") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def test_company_data():
    with open(f"{TEST_DATA_BASE_PATH}company.json") as f:
        return json.load(f)


def _get_user_row(email: str):
    session = session_manager.session_local()
    try:
        return session.query(User).filter_by(email=email.lower()).first()
    finally:
        session.close()


def _get_company_row(email: str):
    session = session_manager.session_local()
    try:
        return session.query(Company).filter_by(email=email.lower()).first()
    finally:
        session.close()


def _get_role_row(company_id: UUID, name: str):
    session = session_manager.session_local()
    try:
        return (
            session.query(Role)
            .join(CompanyRole, CompanyRole.role_id == Role.id)
            .filter(
                CompanyRole.company_id == company_id,
                CompanyRole._closed_at.is_(None),
                Role.name == name,
                Role._closed_at.is_(None),
            )
            .first()
        )
    finally:
        session.close()


def _get_link_row(company_id: UUID, user_id: UUID):
    session = session_manager.session_local()
    try:
        return (
            session.query(AssociationUserCompany)
            .filter_by(company_id=company_id, user_id=user_id, _closed_at=None)
            .first()
        )
    finally:
        session.close()


async def _create_user_if_missing(client: AsyncClient, user: dict):
    existing_user = _get_user_row(user["email"])
    if existing_user:
        session = session_manager.session_local()
        try:
            user_row = session.query(User).filter_by(email=user["email"].lower()).one()
            user_row.first_name = user["first_name"]
            user_row.last_name = user["last_name"]
            user_row.phone_number = user["phone_number"]
            user_row.password = hash_password(user["password"])
            user_row._closed_at = None
            user_row.primary_meta_data = {
                "status": UserAccountStatus.AWAITING_VERIFICATION.name_value,
                "refresh_token_version": 0,
            }
            user_row.secondary_meta_data = {}
            session.commit()
        finally:
            session.close()
        return

    payload = {
        "first_name": user["first_name"],
        "last_name": user["last_name"],
        "phone_number": user["phone_number"],
    }
    response = await client.post(
        "/user/create",
        json=payload,
        headers=get_basic_auth_header(user["email"], user["password"]),
    )
    assert response.status_code in [200, 201], response.text


async def _login_user(client: AsyncClient, user: dict) -> str:
    response = await client.patch(
        "/user/login",
        headers=get_basic_auth_header(user["email"], user["password"]),
    )
    assert response.status_code in [200, 201, 202], response.text
    return response.json()["data"]["access_token"]


async def _create_company_if_missing(
    client: AsyncClient,
    token: str,
    company: dict,
    *,
    owner_email: str,
):
    existing_company = _get_company_row(company["email"])
    if existing_company:
        session = session_manager.session_local()
        try:
            company_row = (
                session.query(Company).filter_by(email=company["email"].lower()).one()
            )
            company_row.name = company["name"]
            company_row.description = company["description"]
            company_row.industry = company["industry"]
            company_row.phone_number = company["phone_number"]
            company_row._closed_at = None
            company_row.primary_meta_data = {
                "address": {
                    "street": "123 Main St",
                    "city": "Johannesburg",
                    "state": "Gauteng",
                    "postal_code": "2000",
                    "country": "South Africa",
                }
            }

            for default_role in CompanyDefaultRoles:
                if not _get_role_row(company_row.id, default_role.name_value):
                    Role.create(
                        session,
                        company_id=company_row.id,
                        name=default_role.name_value,
                        description=default_role.description,
                    )

            owner_row = session.query(User).filter_by(email=owner_email.lower()).one()
            owner_link = (
                session.query(AssociationUserCompany)
                .filter_by(company_id=company_row.id, user_id=owner_row.id)
                .one_or_none()
            )
            if owner_link is None:
                AssociationUserCompany.create(
                    session,
                    company_id=company_row.id,
                    user_id=owner_row.id,
                    role_name=CompanyDefaultRoles.OWNER.name_value,
                )
            else:
                owner_role = Role.role_belongs_to_company(
                    session, company_row.id, CompanyDefaultRoles.OWNER.name_value
                )
                owner_link.role_id = owner_role["id"]
                owner_link._closed_at = None

            session.commit()
        finally:
            session.close()
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
    response = await client.post(
        "/company",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code in [200, 201], response.text


async def _create_role_if_missing(
    client: AsyncClient, *, company_id: int, token: str, role_payload: dict
):
    if _get_role_row(company_id, role_payload["name"]):
        return

    session = session_manager.session_local()
    try:
        role_row = _get_role_row(company_id, role_payload["name"])
        if role_row is not None:
            role_row.description = role_payload["description"]
            role_row._closed_at = None
            session.commit()
            return
    finally:
        session.close()

    response = await client.post(
        f"/company/{company_id}/role",
        json=role_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code in [200, 201], response.text


@pytest.fixture
def get_user_two_otp(test_user_data):
    def _get_token():
        user = test_user_data["user_two"]
        session = session_manager.session_local()
        try:
            user_row = (
                session.query(User).filter_by(email=user["email"].lower()).first()
            )
            if user_row:
                return user_row.primary_meta_data.get("password_reset", {}).get("token")
            return None
        finally:
            session.close()

    return _get_token


@pytest.fixture
async def seed_users(client, test_user_data):
    for key in ("user_one", "user_two", "user_three"):
        await _create_user_if_missing(client, test_user_data[key])


async def _verify_user_account(client: AsyncClient, email: str):
    token = JWTManager().sign_payload(
        {"sub": email, "type": "verification"}, expires_delta=timedelta(minutes=60)
    )
    response = await client.get(f"/user/verify?token={token}")
    assert response.status_code in [200, 201]


@pytest.fixture
async def seed_verified_users(client, seed_users, test_user_data):
    for key in ("user_one", "user_two", "user_three"):
        user = _get_user_row(test_user_data[key]["email"])
        status = (user.primary_meta_data or {}).get("status") if user else None
        if status != UserAccountStatus.ACTIVE.name_value:
            await _verify_user_account(client, test_user_data[key]["email"])


@pytest.fixture
async def login_token(client, seed_verified_users, test_user_data):
    return await _login_user(client, test_user_data["user_one"])


@pytest.fixture
async def login_token_user_two(client, seed_verified_users, test_user_data):
    return await _login_user(client, test_user_data["user_two"])


@pytest.fixture
async def verify_user_one_account(client, test_user_data):
    await _verify_user_account(client, test_user_data["user_one"]["email"])


@pytest.fixture
async def verify_user_two_account(client, test_user_data):
    await _verify_user_account(client, test_user_data["user_two"]["email"])


@pytest.fixture
async def verify_both_users(verify_user_one_account, verify_user_two_account):
    return None


@pytest.fixture
async def seed_companies(client, test_company_data, login_token, login_token_user_two):
    await _create_company_if_missing(
        client,
        login_token,
        test_company_data["company_one"],
        owner_email="user.one@email.com",
    )
    await _create_company_if_missing(
        client,
        login_token_user_two,
        test_company_data["company_two"],
        owner_email="user.two@email.com",
    )
    return {
        "company_one": _get_company_row(test_company_data["company_one"]["email"]).id,
        "company_two": _get_company_row(test_company_data["company_two"]["email"]).id,
    }


@pytest.fixture
async def seed_company_roles(
    client, seed_companies, test_company_data, login_token, login_token_user_two
):
    for role_payload in test_company_data["roles"].values():
        await _create_role_if_missing(
            client,
            company_id=seed_companies["company_one"],
            token=login_token,
            role_payload=role_payload,
        )
        await _create_role_if_missing(
            client,
            company_id=seed_companies["company_two"],
            token=login_token_user_two,
            role_payload=role_payload,
        )
    return seed_companies


@pytest.fixture(scope="session")
def seed_pagination_state():
    owner = {
        "first_name": "Pagy",
        "last_name": "Owner",
        "phone_number": "0333333333",
        "email": "pagination.owner@email.com",
        "password": "secureOwner",
    }
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

    session = session_manager.session_local()
    try:
        owner_row = session.query(User).filter_by(email=owner["email"]).one_or_none()
        if owner_row is None:
            owner_row = User(
                first_name=owner["first_name"],
                last_name=owner["last_name"],
                phone_number=owner["phone_number"],
                email=owner["email"],
                password=hash_password(owner["password"]),
                primary_meta_data={
                    "status": UserAccountStatus.ACTIVE.name_value,
                    "refresh_token_version": 0,
                },
                secondary_meta_data={},
            )
            session.add(owner_row)
            session.flush()
        owner_row.first_name = owner["first_name"]
        owner_row.last_name = owner["last_name"]
        owner_row.phone_number = owner["phone_number"]
        owner_row.password = hash_password(owner["password"])
        owner_row._closed_at = None
        owner_row.primary_meta_data = {
            "status": UserAccountStatus.ACTIVE.name_value,
            "refresh_token_version": 0,
        }
        owner_row.secondary_meta_data = {}
        session.commit()
        session.refresh(owner_row)

        company_ids = []
        for company_data in companies:
            company_row = (
                session.query(Company)
                .filter_by(email=company_data["email"])
                .one_or_none()
            )
            if company_row is None:
                company_row = Company(
                    name=company_data["name"],
                    description=company_data["description"],
                    industry=company_data["industry"],
                    email=company_data["email"],
                    phone_number=company_data["phone_number"],
                    primary_meta_data={
                        "address": {
                            "street": "123 Pagination Road",
                            "city": "Johannesburg",
                            "state": "Gauteng",
                            "postal_code": "2000",
                            "country": "South Africa",
                        }
                    },
                )
                session.add(company_row)
                session.flush()
            company_row.name = company_data["name"]
            company_row.description = company_data["description"]
            company_row.industry = company_data["industry"]
            company_row.phone_number = company_data["phone_number"]
            company_row._closed_at = None
            company_row.primary_meta_data = {
                "address": {
                    "street": "123 Pagination Road",
                    "city": "Johannesburg",
                    "state": "Gauteng",
                    "postal_code": "2000",
                    "country": "South Africa",
                }
            }
            session.commit()
            session.refresh(company_row)
            company_ids.append(company_row.id)

        owner_role_name = CompanyDefaultRoles.OWNER.name_value
        administrator_role_name = CompanyDefaultRoles.ADMINISTRATOR.name_value
        viewer_role_name = CompanyDefaultRoles.VIEWER.name_value

        for company_id in company_ids:
            for default_role in CompanyDefaultRoles:
                if not _get_role_row(company_id, default_role.name_value):
                    Role.create(
                        session,
                        company_id=company_id,
                        name=default_role.name_value,
                        description=default_role.description,
                    )
            session.commit()

        custom_roles = [
            ("User", "Standard user role with limited access."),
            ("Client", "Client role with access to client-specific features."),
        ]
        for role_name, description in custom_roles:
            if not _get_role_row(company_ids[0], role_name):
                Role.create(
                    session,
                    company_id=company_ids[0],
                    name=role_name,
                    description=description,
                )
        session.commit()

        for company_id in company_ids:
            owner_link = (
                session.query(AssociationUserCompany)
                .filter_by(company_id=company_id, user_id=owner_row.id)
                .one_or_none()
            )
            if owner_link is None:
                owner_link = AssociationUserCompany.create(
                    session,
                    company_id=company_id,
                    user_id=owner_row.id,
                    role_name=owner_role_name,
                )
            else:
                owner_role = Role.role_belongs_to_company(
                    session, company_id, owner_role_name
                )
                owner_link.role_id = owner_role["id"]
                owner_link._closed_at = None
            session.commit()

        user_ids = []
        for user_data in extra_users:
            user_row = (
                session.query(User).filter_by(email=user_data["email"]).one_or_none()
            )
            if user_row is None:
                user_row = User(
                    first_name=user_data["first_name"],
                    last_name=user_data["last_name"],
                    phone_number=user_data["phone_number"],
                    email=user_data["email"],
                    password=hash_password(user_data["password"]),
                    primary_meta_data={
                        "status": UserAccountStatus.ACTIVE.name_value,
                        "refresh_token_version": 0,
                    },
                    secondary_meta_data={},
                )
                session.add(user_row)
                session.flush()
            user_row.first_name = user_data["first_name"]
            user_row.last_name = user_data["last_name"]
            user_row.phone_number = user_data["phone_number"]
            user_row.password = hash_password(user_data["password"])
            user_row._closed_at = None
            user_row.primary_meta_data = {
                "status": UserAccountStatus.ACTIVE.name_value,
                "refresh_token_version": 0,
            }
            user_row.secondary_meta_data = {}
            session.commit()
            session.refresh(user_row)
            user_ids.append(user_row.id)

        desired_links = [
            (company_ids[0], user_ids[0], administrator_role_name),
            (company_ids[0], user_ids[1], viewer_role_name),
            (company_ids[0], user_ids[2], viewer_role_name),
            (company_ids[1], user_ids[0], viewer_role_name),
            (company_ids[1], user_ids[1], administrator_role_name),
            (company_ids[2], user_ids[2], administrator_role_name),
            (company_ids[3], user_ids[0], viewer_role_name),
        ]

        for company_id, user_id, role_name in desired_links:
            existing_link = (
                session.query(AssociationUserCompany)
                .filter_by(company_id=company_id, user_id=user_id)
                .one_or_none()
            )
            if existing_link is None:
                AssociationUserCompany.create(
                    session,
                    company_id=company_id,
                    user_id=user_id,
                    role_name=role_name,
                )
            else:
                role = Role.role_belongs_to_company(session, company_id, role_name)
                existing_link.role_id = role["id"]
                existing_link._closed_at = None
            session.commit()

        owner_token = (
            JWTManager()
            .sign_jwt(
                UserReadModel(
                    id=owner_row.id,
                    first_name=owner_row.first_name,
                    last_name=owner_row.last_name,
                    email=owner_row.email,
                    phone_number=owner_row.phone_number,
                    status=UserAccountStatus.ACTIVE.name_value,
                    is_superuser=owner_row.is_superuser,
                )
            )
            .access_token
        )

        return {
            "owner": owner,
            "owner_id": owner_row.id,
            "owner_token": owner_token,
            "companies": company_ids,
            "role_company_id": company_ids[0],
            "users_company_id": company_ids[0],
            "user_company_ids": company_ids,
            "users": user_ids,
        }
    finally:
        session.close()
