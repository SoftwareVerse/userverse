import importlib
from pathlib import Path
from textwrap import dedent
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

import app.services.mailer as mailer_module
from app.configs import Settings, _SettingsProxy
import app.repository.database.session_manager as session_manager
from app.services.company.user import CompanyUserService
from app.models.company.company import CompanyQueryParamsModel
from app.models.user.response_messages import UserResponseMessages
from app.models.user.user import UserReadModel
from app.services.user.basic_auth import UserBasicAuthService
from app.services.user.profile import UserProfileService
from app.services.user.verification import UserVerificationService
from app.utils.app_error import AppError
from app.utils.shared_context import SharedContext
from app.models.phone_number import validate_phone_number_format
from app.models.tags import UserverseApiTag
from app.models.user.account_status import UserAccountStatus
from app.models.user.password import OTPValidationRequest, PasswordResetRequest
from app.models.user.user import UserUpdateModel
from app.utils.hash_password import UnknownHashError, verify_password
from app.utils.parsing import normalize_origins
from app.utils.project_metadata import load_project_defaults


def test_normalize_origins_handles_supported_shapes():
    assert normalize_origins(None) == []
    assert normalize_origins("   ") == []
    assert normalize_origins([" https://api.example.com ", "", 123]) == [
        "https://api.example.com",
        "123",
    ]
    assert normalize_origins('["http://one.test", " http://two.test "]') == [
        "http://one.test",
        "http://two.test",
    ]
    assert normalize_origins("[not-json") == ["[not-json"]
    assert normalize_origins("http://one.test, http://two.test") == [
        "http://one.test",
        "http://two.test",
    ]
    assert normalize_origins(42) == ["42"]


def test_project_metadata_loads_defaults_for_missing_or_invalid_files(tmp_path: Path):
    assert load_project_defaults(tmp_path)["name"] == "Userverse"

    invalid_root = tmp_path / "invalid"
    invalid_root.mkdir()
    (invalid_root / "pyproject.toml").write_text("not = [valid", encoding="utf-8")

    assert load_project_defaults(invalid_root)["version"] == "0.1.0"


def test_project_metadata_loads_project_fields(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text(
        dedent("""
            [project]
            name = "customverse"
            version = "1.2.3"
            description = "Custom service"

            [project.urls]
            Repository = "https://example.com/repo"
            Documentation = "https://example.com/docs"
            """).strip(),
        encoding="utf-8",
    )

    assert load_project_defaults(tmp_path) == {
        "name": "customverse",
        "version": "1.2.3",
        "description": "Custom service",
        "repository": "https://example.com/repo",
        "documentation": "https://example.com/docs",
    }


def test_settings_builds_database_urls_for_supported_backends(monkeypatch):
    for name in (
        "DATABASE_URL",
        "DB_TYPE",
        "DB_USER",
        "DB_PASSWORD",
        "DB_NAME",
        "DB_HOST",
        "DB_PORT",
    ):
        monkeypatch.delenv(name, raising=False)

    sqlite_settings = Settings(
        ENVIRONMENT="QA",
        DB_TYPE="sqlite",
        DB_NAME="local.db",
        _env_file=None,
    )
    assert sqlite_settings.ENVIRONMENT == "qa"
    assert sqlite_settings.DATABASE_URL == "sqlite:///local.db"

    postgres_settings = Settings(
        DB_TYPE="postgresql",
        DB_USER="user",
        DB_PASSWORD="pass",
        DB_NAME="app",
        DB_HOST="db.local",
        DB_PORT=5433,
        _env_file=None,
    )
    assert (
        postgres_settings.DATABASE_URL
        == "postgresql+psycopg2://user:pass@db.local:5433/app"
    )

    mysql_settings = Settings(
        DB_TYPE="mysql",
        DB_USER="user",
        DB_PASSWORD="pass",
        DB_NAME="app",
        DB_HOST="db.local",
        DB_PORT=3307,
        _env_file=None,
    )
    assert mysql_settings.DATABASE_URL == "mysql://user:pass@db.local:3307/app"

    fallback_settings = Settings(
        ENVIRONMENT="review",
        DB_TYPE="postgresql",
        JWT_SECRET="review-secret",
        _env_file=None,
    )
    assert fallback_settings.DATABASE_URL == "sqlite:///./review.db"
    assert fallback_settings.PROJECT_ROOT.name == "userverse"


def test_settings_defaults_use_safe_db_and_cors_defaults():
    default_settings = Settings(
        DB_AUTO_CREATE=False,
        CORS_ALLOWED=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        JWT_SECRET="development-secret",
        _env_file=None,
    )

    assert default_settings.DB_AUTO_CREATE is False
    assert default_settings.CORS_ALLOWED == [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


def test_settings_normalize_server_url_and_cors_lists(monkeypatch):
    monkeypatch.setenv("SERVER_URL", "http://localhost:8500/")
    monkeypatch.setenv("CORS_ALLOWED", '["http://one.test", " http://two.test "]')
    monkeypatch.setenv("CORS_BLOCKED", '["http://two.test"]')

    normalized = Settings(JWT_SECRET="development-secret", _env_file=None)

    assert normalized.SERVER_URL == "http://localhost:8500"
    assert normalized.CORS_ALLOWED == ["http://one.test", "http://two.test"]
    assert normalized.CORS_BLOCKED == ["http://two.test"]


def test_settings_rejects_default_jwt_secret_outside_safe_environments(monkeypatch):
    monkeypatch.delenv("TESTING", raising=False)

    with pytest.raises(
        ValidationError,
        match="JWT_SECRET must be explicitly set outside development/testing environments",
    ):
        Settings(
            ENVIRONMENT="production",
            JWT_SECRET="secret1234",
            _env_file=None,
        )

    production_settings = Settings(
        ENVIRONMENT="production",
        JWT_SECRET="strong-production-secret",
        _env_file=None,
    )
    assert production_settings.JWT_SECRET == "strong-production-secret"

    development_settings = Settings(
        ENVIRONMENT="development",
        JWT_SECRET="secret1234",
        _env_file=None,
    )
    assert development_settings.JWT_SECRET == "secret1234"

    testing_settings = Settings(
        ENVIRONMENT="production",
        TESTING=True,
        JWT_SECRET="secret1234",
        _env_file=None,
    )
    assert testing_settings.JWT_SECRET == "secret1234"


def test_settings_proxy_tracks_overrides_and_missing_deletes(monkeypatch):
    proxy = _SettingsProxy()
    proxy.SERVER_URL = "http://override.test"
    assert proxy.SERVER_URL == "http://override.test"

    del proxy.SERVER_URL
    with pytest.raises(AttributeError):
        del proxy.SERVER_URL

    object.__setattr__(proxy, "_overrides", {"CUSTOM_VALUE": "set"})
    monkeypatch.setattr(
        "app.configs.get_settings",
        lambda: Settings(DATABASE_URL="sqlite:///proxy.db", _env_file=None),
    )

    assert "CUSTOM_VALUE" in dir(proxy)

    object.__setattr__(proxy, "_overrides", {})
    proxy._overrides = {"ANOTHER": "value"}
    assert proxy._overrides == {"ANOTHER": "value"}


def test_default_db_singleton_is_reused(monkeypatch):
    fake_manager = object()
    monkeypatch.setattr(session_manager, "_default_db", None)
    monkeypatch.setattr(
        session_manager,
        "DatabaseSessionManager",
        lambda: fake_manager,
    )

    assert session_manager._get_default_db() is fake_manager
    assert session_manager._get_default_db() is fake_manager


def test_build_settings_env_snapshot_reads_current_environment(monkeypatch):
    monkeypatch.setenv("SERVER_URL", "http://snapshot.test")

    from app.utils.env import build_settings_env_snapshot

    snapshot = dict(build_settings_env_snapshot())

    assert snapshot["SERVER_URL"] == "http://snapshot.test"


def test_strip_matching_quotes_removes_matching_wrappers():
    from app.utils.env import strip_matching_quotes

    assert strip_matching_quotes('"quoted"') == "quoted"
    assert strip_matching_quotes("'quoted'") == "quoted"
    assert strip_matching_quotes("plain") == "plain"


def test_simple_request_models_and_enums():
    assert PasswordResetRequest(email="user@example.com").email == "user@example.com"
    assert OTPValidationRequest(otp="123456").otp == "123456"

    with pytest.raises(ValidationError):
        PasswordResetRequest(email="not-an-email")

    assert UserAccountStatus.ACTIVE.name_value == "Active"
    assert UserAccountStatus.ACTIVE.description == "Verified and allowed to log in"
    assert {
        "name": "Company Management",
        "description": "Create and manage companies",
    } in UserverseApiTag.list()


def test_phone_number_validator_normalizes_and_rejects_invalid_values():
    assert validate_phone_number_format(None) is None
    assert validate_phone_number_format("+27123456789") == "+27123456789"
    assert validate_phone_number_format("011 222 3333") == "011 222 3333"
    assert UserUpdateModel(phone_number=None).phone_number is None

    with pytest.raises(ValueError, match="Invalid phone number."):
        validate_phone_number_format("+27123")

    with pytest.raises(ValueError, match="Invalid phone number"):
        validate_phone_number_format("+1")

    with pytest.raises(ValueError, match="Invalid phone number format"):
        validate_phone_number_format("abc")


def test_verify_password_rejects_malformed_bcrypt_hash():
    malformed_hash = "$2b$" + "x" * 56

    with pytest.raises(UnknownHashError, match="hash could not be identified"):
        verify_password("secret", malformed_hash)


def test_mail_service_renders_and_sends_template(monkeypatch):
    reloaded_mailer = importlib.reload(mailer_module)
    send_email = Mock()
    monkeypatch.setattr(
        reloaded_mailer,
        "render_email_template",
        lambda template_name, context: f"{template_name}:{context['user_name']}",
    )
    monkeypatch.setattr(reloaded_mailer, "send_email", send_email)

    reloaded_mailer.MailService.send_template_email(
        to="user@example.com",
        subject="Subject",
        template_name="welcome.html",
        context={"user_name": "Jane"},
    )

    send_email.assert_called_once_with(
        to="user@example.com",
        subject="Subject",
        html_body="welcome.html:Jane",
        reason="template:welcome.html",
    )


def test_verification_service_rejects_missing_email(monkeypatch):
    monkeypatch.setattr(
        "app.services.user.verification.JWTManager.decode_verification_token",
        lambda self, token: {"type": "verification"},
    )

    with pytest.raises(AppError) as exc_info:
        UserVerificationService(session=object()).verify_user_account("token")

    assert exc_info.value.status_code == 400
    assert (
        exc_info.value.detail["message"]
        == UserResponseMessages.EMAIL_VERIFICATION_FAILED.value
    )


def test_verification_service_rejects_wrong_type_after_decode(monkeypatch):
    monkeypatch.setattr(
        "app.services.user.verification.JWTManager.decode_verification_token",
        lambda self, token: {"sub": "user@example.com", "type": "refresh"},
    )

    with pytest.raises(AppError) as exc_info:
        UserVerificationService(session=object()).verify_user_account("token")

    assert exc_info.value.status_code == 400
    assert (
        exc_info.value.detail["message"]
        == UserResponseMessages.INVALID_VERIFICATION_TOKEN.value
    )


def test_verification_service_rejects_non_pending_accounts(monkeypatch):
    monkeypatch.setattr(
        "app.services.user.verification.JWTManager.decode_verification_token",
        lambda self, token: {"sub": "user@example.com", "type": "verification"},
    )

    class FakeUserRepository:
        def __init__(self, session):
            self.session = session

        def get_user_by_email(self, email):
            return UserReadModel(
                id=1,
                email=email,
                first_name="Jane",
                last_name="Doe",
                phone_number="+27123456789",
                status=UserAccountStatus.SUSPENDED.name_value,
                is_superuser=False,
            )

    monkeypatch.setattr(
        "app.services.user.verification.UserRepository",
        FakeUserRepository,
    )

    with pytest.raises(AppError) as exc_info:
        UserVerificationService(session=object()).verify_user_account("token")

    assert exc_info.value.status_code == 403
    assert (
        exc_info.value.detail["message"] == "User account is not awaiting verification"
    )


def test_send_verification_email_logs_dispatch_failures(monkeypatch):
    captured_errors = []
    monkeypatch.setattr(
        "app.services.user.basic_auth.MailService.send_template_email",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("smtp down")),
    )
    monkeypatch.setattr(
        "app.services.user.basic_auth.logger.error",
        lambda message, extra: captured_errors.append((message, extra)),
    )

    user = UserReadModel(
        id=1,
        email="user@example.com",
        first_name="Jane",
        last_name="Doe",
        phone_number="+27123456789",
        status=UserAccountStatus.ACTIVE.name_value,
        is_superuser=False,
    )
    context = SharedContext(db_session=object(), user=user)

    UserBasicAuthService(context).send_verification_email()

    assert captured_errors[0][0] == "Verification email dispatch failed"
    assert captured_errors[0][1]["extra"]["error"] == "smtp down"


def test_company_user_service_sends_company_invite(monkeypatch):
    sent_messages = []
    monkeypatch.setattr(
        "app.services.company.user.MailService.send_template_email",
        lambda **kwargs: sent_messages.append(kwargs),
    )

    acting_user = UserReadModel(
        id=99,
        email="admin@example.com",
        first_name="Admin",
        last_name="User",
        phone_number="+27123456789",
        status=UserAccountStatus.ACTIVE.name_value,
        is_superuser=False,
    )
    added_user = UserReadModel(
        id=2,
        email="invitee@example.com",
        first_name="Invited",
        last_name="Member",
        phone_number="+27123456789",
        status=UserAccountStatus.ACTIVE.name_value,
        is_superuser=False,
    )
    added_company_user = type(
        "AddedCompanyUser",
        (),
        {**added_user.model_dump(), "role_name": "Viewer"},
    )()
    company = type("Company", (), {"name": "Acme Co"})()

    service = CompanyUserService(SharedContext(db_session=object(), user=acting_user))
    monkeypatch.setattr(service, "check_if_user_is_in_company", lambda **kwargs: True)
    monkeypatch.setattr(
        service.company_user_repository,
        "is_user_linked_to_company",
        lambda **kwargs: True,
    )
    monkeypatch.setattr(
        service.company_user_repository,
        "add_user_to_company",
        lambda **kwargs: added_company_user,
    )
    monkeypatch.setattr(
        service.company_repository,
        "get_company_by_id",
        lambda company_id: company,
    )

    result = service.add_user_to_company(
        company_id=1,
        payload=type(
            "Payload", (), {"email": "invitee@example.com", "role": "Viewer"}
        )(),
    )

    assert result.email == "invitee@example.com"
    assert sent_messages == [
        {
            "to": "invitee@example.com",
            "subject": "Userverse Company Invitation",
            "template_name": "company_invite.html",
            "context": {
                "invitee": "Invited Member",
                "company": "Acme Co",
                "role": "Viewer",
                "app_name": "Userverse",
            },
        }
    ]


def test_company_user_service_logs_invite_failures(monkeypatch):
    captured_errors = []
    monkeypatch.setattr(
        "app.services.company.user.MailService.send_template_email",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("smtp down")),
    )
    monkeypatch.setattr(
        "app.services.company.user.logger.error",
        lambda message, extra: captured_errors.append((message, extra)),
    )

    acting_user = UserReadModel(
        id=99,
        email="admin@example.com",
        first_name="Admin",
        last_name="User",
        phone_number="+27123456789",
        status=UserAccountStatus.ACTIVE.name_value,
        is_superuser=False,
    )
    service = CompanyUserService(SharedContext(db_session=object(), user=acting_user))

    service.send_company_invite(
        invitee_email="invitee@example.com",
        invitee_name="Invited Member",
        company_name="Acme Co",
        role_name="Viewer",
    )

    assert captured_errors[0][0] == "Company invite dispatch failed"
    assert captured_errors[0][1]["extra"]["error"] == "smtp down"


def test_company_user_repository_ensure_user_linked_to_company_raises(monkeypatch):
    from app.models.company.response_messages import CompanyResponseMessages
    from app.repository.company_user import CompanyUserRepository
    from app.utils.app_error import AppError

    repository = CompanyUserRepository(session=object())
    monkeypatch.setattr(
        repository,
        "is_user_linked_to_company",
        lambda user_id, company_id, role_name=None: False,
    )

    with pytest.raises(AppError) as exc_info:
        repository.ensure_user_linked_to_company(user_id=1, company_id=1)

    assert (
        exc_info.value.detail["message"]
        == CompanyResponseMessages.UNAUTHORIZED_COMPANY_ACCESS.value
    )


def test_company_user_repository_ensure_user_linked_to_company_returns_true(
    monkeypatch,
):
    from app.repository.company_user import CompanyUserRepository

    repository = CompanyUserRepository(session=object())
    monkeypatch.setattr(
        repository,
        "is_user_linked_to_company",
        lambda user_id, company_id, role_name=None: True,
    )

    assert repository.ensure_user_linked_to_company(user_id=1, company_id=1) is True


def test_user_repository_get_user_by_id_wraps_unexpected_errors(monkeypatch):
    from app.repository.user import UserRepository

    repository = UserRepository(db_session=object())

    class FailingQuery:
        def filter(self, *args, **kwargs):
            raise RuntimeError("db blew up")

    monkeypatch.setattr(repository, "_active_user_query", lambda: FailingQuery())

    with pytest.raises(AppError) as exc_info:
        repository.get_user_by_id(1)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail["message"] == UserResponseMessages.USER_NOT_FOUND.value


def test_user_repository_get_user_by_email_rehashes_plaintext_password(monkeypatch):
    from app.repository.user import UserRepository

    class FakeUser:
        id = 1
        first_name = "Jane"
        last_name = "Doe"
        email = "user@example.com"
        phone_number = "+27123456789"
        is_superuser = False
        password = "plain-secret"
        primary_meta_data = {"status": UserAccountStatus.ACTIVE.name_value}

    fake_user = FakeUser()
    session = Mock()
    repository = UserRepository(db_session=session)

    class FakeQuery:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return fake_user

    monkeypatch.setattr(repository, "_active_user_query", lambda: FakeQuery())
    monkeypatch.setattr(
        "app.repository.user.verify_password",
        lambda password, hashed: (_ for _ in ()).throw(UnknownHashError("bad hash")),
    )
    monkeypatch.setattr(
        "app.repository.user.hash_password",
        lambda password: f"rehash::{password}",
    )

    user = repository.get_user_by_email("user@example.com", "plain-secret")

    assert user.email == "user@example.com"
    assert fake_user.password == "rehash::plain-secret"
    session.commit.assert_called_once()
    session.refresh.assert_called_once_with(fake_user)


def test_user_repository_create_user_handles_unique_constraint_integrity_error(
    monkeypatch,
):
    from sqlalchemy.exc import IntegrityError
    from app.repository.user import UserRepository

    session = Mock()
    repository = UserRepository(db_session=session)
    monkeypatch.setattr(repository, "_active_user_query", lambda: Mock(filter=lambda *a, **k: Mock(first=lambda: None)))

    def raise_integrity(**kwargs):
        raise IntegrityError("insert", {}, Exception("UNIQUE constraint failed: user.email"))

    monkeypatch.setattr(repository, "create", raise_integrity)

    with pytest.raises(AppError) as exc_info:
        repository.create_user({"email": "user@example.com", "password": "secret"})

    assert exc_info.value.status_code == 409
    assert (
        exc_info.value.detail["message"]
        == UserResponseMessages.USER_ALREADY_EXISTS.value
    )
    session.rollback.assert_called_once()


def test_user_repository_update_user_raises_when_missing(monkeypatch):
    from app.repository.user import UserRepository

    repository = UserRepository(db_session=object())

    class FakeQuery:
        def filter(self, *args, **kwargs):
            return self

        def one_or_none(self):
            return None

    monkeypatch.setattr(repository, "_active_user_query", lambda: FakeQuery())

    with pytest.raises(AppError) as exc_info:
        repository.update_user(1, {"first_name": "Updated"})

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["message"] == UserResponseMessages.USER_UPDATE_FAILED.value


def test_user_repository_update_user_status_raises_when_missing(monkeypatch):
    from app.repository.user import UserRepository

    repository = UserRepository(db_session=object())

    class FakeQuery:
        def filter(self, *args, **kwargs):
            return self

        def one_or_none(self):
            return None

    monkeypatch.setattr(repository, "_active_user_query", lambda: FakeQuery())

    with pytest.raises(AppError) as exc_info:
        repository.update_user_status(1, UserAccountStatus.ACTIVE.name_value)

    assert exc_info.value.status_code == 400
    assert (
        exc_info.value.detail["message"]
        == UserResponseMessages.USER_ACCOUNT_STATUS_UPDATE_FAILED.value
    )


def test_user_repository_increment_refresh_token_version_raises_when_missing(
    monkeypatch,
):
    from app.repository.user import UserRepository

    repository = UserRepository(db_session=object())

    class FakeQuery:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return None

    monkeypatch.setattr(repository, "_active_user_query", lambda: FakeQuery())

    with pytest.raises(AppError) as exc_info:
        repository.increment_refresh_token_version(1)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail["message"] == UserResponseMessages.USER_NOT_FOUND.value


def test_user_repository_delete_user_raises_when_missing(monkeypatch):
    from app.repository.user import UserRepository

    repository = UserRepository(db_session=object())

    class FakeQuery:
        def filter(self, *args, **kwargs):
            return self

        def one_or_none(self):
            return None

    monkeypatch.setattr(repository, "_active_user_query", lambda: FakeQuery())

    with pytest.raises(AppError) as exc_info:
        repository.delete_user(1)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail["message"] == UserResponseMessages.USER_NOT_FOUND.value


def test_user_profile_service_get_user_prefers_id(monkeypatch):
    acting_user = UserReadModel(
        id=9,
        email="admin@example.com",
        first_name="Admin",
        last_name="User",
        phone_number="+27123456789",
        status=UserAccountStatus.ACTIVE.name_value,
        is_superuser=False,
    )
    service = UserProfileService(SharedContext(db_session=object(), user=acting_user))
    expected = UserReadModel(
        id=1,
        email="target@example.com",
        first_name="Target",
        last_name="User",
        phone_number="+27123456789",
        status=UserAccountStatus.ACTIVE.name_value,
        is_superuser=False,
    )
    monkeypatch.setattr(service.user_repository, "get_user_by_id", lambda user_id: expected)
    monkeypatch.setattr(
        service.user_repository,
        "get_user_by_email",
        lambda email: (_ for _ in ()).throw(AssertionError("email path should not be used")),
    )

    result = service.get_user(user_id=1, user_email="ignored@example.com")

    assert result == expected


def test_user_profile_service_get_user_raises_without_identifier():
    acting_user = UserReadModel(
        id=9,
        email="admin@example.com",
        first_name="Admin",
        last_name="User",
        phone_number="+27123456789",
        status=UserAccountStatus.ACTIVE.name_value,
        is_superuser=False,
    )
    service = UserProfileService(SharedContext(db_session=object(), user=acting_user))

    with pytest.raises(AppError) as exc_info:
        service.get_user()

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["message"] == UserResponseMessages.USER_NOT_FOUND.value


def test_user_profile_service_update_user_handles_phone_and_invalid_request(
    monkeypatch,
):
    acting_user = UserReadModel(
        id=9,
        email="admin@example.com",
        first_name="Admin",
        last_name="User",
        phone_number="+27123456789",
        status=UserAccountStatus.ACTIVE.name_value,
        is_superuser=False,
    )
    service = UserProfileService(SharedContext(db_session=object(), user=acting_user))
    captured = {}
    expected = UserReadModel(
        id=9,
        email="admin@example.com",
        first_name="Admin",
        last_name="User",
        phone_number="011 222 3333",
        status=UserAccountStatus.ACTIVE.name_value,
        is_superuser=False,
    )

    def fake_update_user(user_id, data):
        captured["user_id"] = user_id
        captured["data"] = data
        return expected

    monkeypatch.setattr(service.user_repository, "update_user", fake_update_user)
    monkeypatch.setattr("app.services.user.profile.hash_password", lambda password: f"hashed::{password}")

    result = service.update_user(
        9,
        UserUpdateModel(phone_number="011 222 3333", password="secret"),
    )

    assert result == expected
    assert captured == {
        "user_id": 9,
        "data": {"phone_number": "011 222 3333", "password": "hashed::secret"},
    }

    with pytest.raises(AppError) as exc_info:
        service.update_user(9, UserUpdateModel())

    assert exc_info.value.status_code == 400
    assert (
        exc_info.value.detail["message"]
        == UserResponseMessages.INVALID_REQUEST_MESSAGE.value
    )


def test_user_profile_service_get_user_companies_and_delete_user(monkeypatch):
    acting_user = UserReadModel(
        id=9,
        email="admin@example.com",
        first_name="Admin",
        last_name="User",
        phone_number="+27123456789",
        status=UserAccountStatus.ACTIVE.name_value,
        is_superuser=False,
    )
    service = UserProfileService(SharedContext(db_session=object(), user=acting_user))
    params = CompanyQueryParamsModel(limit=10, page=1)
    expected = {"records": [], "pagination": {"limit": 10, "current_page": 1}}
    captured = {}

    def fake_get_user_companies(user_id, params):
        captured["companies"] = (user_id, params)
        return expected

    monkeypatch.setattr(
        service.company_repository,
        "get_user_companies",
        fake_get_user_companies,
    )
    monkeypatch.setattr(
        service.user_repository,
        "delete_user",
        lambda user_id: captured.setdefault("deleted", user_id),
    )

    service.get_user_companies(params)
    service.delete_user(9)

    assert captured["companies"] == (9, params)
    assert captured["deleted"] == 9


def test_shared_context_safe_json_returns_scalars_unchanged():
    assert SharedContext.safe_json("plain") == "plain"
