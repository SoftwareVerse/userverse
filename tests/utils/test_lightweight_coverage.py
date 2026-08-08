import importlib
import runpy
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path
from textwrap import dedent
from unittest.mock import Mock
from uuid import uuid4

import pytest
from pydantic import ValidationError

import app.services.mailer as mailer_module
import app.exceptions as exceptions_module
import app.main as main_module
from app.api.routers import roles as global_roles_router
from app.api.routers.company import roles as company_roles_router
from app.configs import Settings, _SettingsProxy
import app.repository.database.session_manager as session_manager
from app.repository.company import CompanyRepository
from app.repository.company_role import CompanyRoleAssignmentRepository, RoleRepository
from app.services.company.company import CompanyService
from app.services.company.role import RoleService
from app.services.company.user import CompanyUserService
from app.models.company.company import CompanyQueryParamsModel
from app.models.company.company import CompanyCreateModel, CompanyUpdateModel
from app.models.company.response_messages import (
    CompanyResponseMessages,
    CompanyRoleResponseMessages,
    CompanyUserResponseMessages,
)
from app.models.company.roles import (
    RoleAssignCompaniesModel,
    RoleCreateModel,
    RoleDeleteModel,
    RoleQueryParamsModel,
    RoleReadModel,
    RoleUpdateModel,
)
from app.models.generic_pagination import PaginatedResponse
from app.models.user.response_messages import UserResponseMessages
from app.models.user.user import UserReadModel
from app.services.user.basic_auth import UserBasicAuthService
from app.services.user.password import UserPasswordService
from app.services.user.profile import UserProfileService
from app.services.user.verification import UserVerificationService
from app.utils.app_error import AppError
from app.utils.shared_context import SharedContext
from app.models.phone_number import validate_phone_number_format
from app.models.tags import UserverseApiTag
from app.models.user.account_status import UserAccountStatus
from app.models.user.password import (
    MagicLinkPasswordResetConfirmRequest,
    OTPValidationRequest,
    PasswordResetMethod,
    PasswordResetRequest,
)
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
    monkeypatch.setenv("FRONTEND_URL", "https://app.example.com/reset-password/")
    monkeypatch.setenv("PASSWORD_RESET_EXPIRY_MINUTES", "45")
    monkeypatch.setenv("CORS_ALLOWED", '["http://one.test", " http://two.test "]')
    monkeypatch.setenv("CORS_BLOCKED", '["http://two.test"]')

    normalized = Settings(JWT_SECRET="development-secret", _env_file=None)

    assert normalized.SERVER_URL == "http://localhost:8500"
    assert normalized.FRONTEND_URL == "https://app.example.com/reset-password"
    assert normalized.PASSWORD_RESET_EXPIRY_MINUTES == 45
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
    assert (
        PasswordResetRequest(email="user@example.com").method == PasswordResetMethod.OTP
    )
    assert OTPValidationRequest(otp="123456").otp == "123456"
    assert (
        MagicLinkPasswordResetConfirmRequest(
            token="reset-token", new_password="Secret123!"
        ).token
        == "reset-token"
    )

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


def test_password_service_helpers_use_shared_frontend_and_expiry(monkeypatch):
    service = UserPasswordService(session=object())
    from app.services.user.password import settings as password_settings

    previous_overrides = dict(password_settings._overrides)
    object.__setattr__(
        password_settings,
        "_overrides",
        {
            **previous_overrides,
            "FRONTEND_URL": "https://app.example.com/reset-password",
            "PASSWORD_RESET_EXPIRY_MINUTES": 45,
            "APP_NAME": "Userverse",
        },
    )
    try:
        assert service.password_reset_expiry == timedelta(minutes=45)
        assert (
            service.build_magic_reset_url("token123")
            == "https://app.example.com/reset-password?token=token123"
        )

        otp_context = service._build_email_context(
            method=PasswordResetMethod.OTP,
            token="123456",
            user_name="Jane",
        )
        assert otp_context == {
            "user_name": "Jane",
            "app_name": "Userverse",
            "otp": "123456",
        }

        magic_context = service._build_email_context(
            method=PasswordResetMethod.MAGIC_LINK,
            token="token123",
            user_name="Jane",
        )
        assert magic_context == {
            "user_name": "Jane",
            "app_name": "Userverse",
            "reset_url": "https://app.example.com/reset-password?token=token123",
            "expires_in": "45 minutes",
        }
    finally:
        object.__setattr__(password_settings, "_overrides", previous_overrides)


def test_password_service_request_logs_and_succeeds_when_sync_email_send_fails(
    monkeypatch,
):
    class FakeUser:
        email = "user@example.com"
        first_name = "Jane"
        last_name = "Doe"

    fake_repo = Mock()
    fake_repo.get_user_record_by_email.return_value = FakeUser()
    fake_password_repo = Mock()

    monkeypatch.setattr(
        "app.services.user.password.UserRepository",
        lambda session: fake_repo,
    )
    monkeypatch.setattr(
        "app.services.user.password.UserPasswordRepository",
        lambda session: fake_password_repo,
    )
    monkeypatch.setattr(
        "app.services.user.password.PASSWORD_RESET_RATE_LIMITER.check",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        "app.services.user.password.MailService.send_template_email",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("smtp down")),
    )
    logger_error = Mock()
    monkeypatch.setattr("app.services.user.password.logger.error", logger_error)

    service = UserPasswordService(session=object())
    response = service.request_password_reset("user@example.com")

    assert (
        response.message
        == "If an account exists for that email, we’ve sent a reset link."
    )
    fake_password_repo.create_password_reset_record.assert_called_once()
    logger_error.assert_called_once()


def test_password_service_reset_with_token_rejects_known_user_with_invalid_token_verification(
    monkeypatch,
):
    fake_user = Mock(email="user@example.com")
    fake_user_repo = Mock()
    fake_user_repo.get_user_record_by_password_reset_token.return_value = fake_user
    fake_password_repo = Mock()
    fake_password_repo.verify_password_reset_token.return_value = False

    monkeypatch.setattr(
        "app.services.user.password.UserRepository",
        lambda session: fake_user_repo,
    )
    monkeypatch.setattr(
        "app.services.user.password.UserPasswordRepository",
        lambda session: fake_password_repo,
    )

    service = UserPasswordService(session=object())
    with pytest.raises(AppError) as exc_info:
        service.reset_password_with_token(token="bad", new_password="Secret123!")

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["message"] == "Magic link verification failed"
    assert (
        exc_info.value.detail["error"]
        == "Invalid reset token, does not match or expired"
    )


def test_password_service_validate_otp_raises_value_error_when_repository_returns_none(
    monkeypatch,
):
    fake_user_repo = Mock()
    fake_user_repo.get_user_by_email.return_value = None
    monkeypatch.setattr(
        "app.services.user.password.UserRepository",
        lambda session: fake_user_repo,
    )

    service = UserPasswordService(session=object())
    with pytest.raises(ValueError, match=UserResponseMessages.USER_NOT_FOUND.value):
        service.validate_otp_and_change_password(
            "user@example.com",
            "123456",
            "Secret123!",
        )


def test_basic_auth_service_does_not_resend_for_active_user(monkeypatch):
    context = Mock()
    context.db_session = object()
    context.configs = Mock(REQUIRE_EMAIL_VERIFICATION=True)
    user = Mock(status=UserAccountStatus.ACTIVE.name_value)

    monkeypatch.setattr(
        "app.services.user.basic_auth.UserRepository",
        lambda session: Mock(),
    )

    service = UserBasicAuthService(context)
    service.send_verification_email = Mock()

    service._resend_verification_email_for_pending_login(user)

    service.send_verification_email.assert_not_called()


def test_user_password_repository_handles_missing_user_and_missing_expiry(monkeypatch):
    from app.repository.user_password import UserPasswordRepository

    repository = UserPasswordRepository(Mock())

    class EmptyQuery:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return None

    monkeypatch.setattr(repository, "_base_query", lambda: EmptyQuery())
    with pytest.raises(AppError) as exc_info:
        repository._get_user("missing@example.com")
    assert exc_info.value.status_code == 404

    class FakeUser:
        primary_meta_data = {
            "password_reset": {
                "method": PasswordResetMethod.OTP.value,
                "token": "123456",
            }
        }

    monkeypatch.setattr(repository, "_get_user", lambda email: FakeUser())
    assert (
        repository.verify_password_reset_token(
            "user@example.com",
            method=PasswordResetMethod.OTP,
            token="123456",
        )
        is False
    )


def test_user_password_repository_verifies_unexpired_token(monkeypatch):
    from app.repository.user_password import UserPasswordRepository

    repository = UserPasswordRepository(Mock())
    future_expiry = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()

    class FakeUser:
        primary_meta_data = {
            "password_reset": {
                "method": PasswordResetMethod.MAGIC_LINK.value,
                "token": "token123",
                "expires_at": future_expiry,
            }
        }

    monkeypatch.setattr(repository, "_get_user", lambda email: FakeUser())
    assert (
        repository.verify_password_reset_token(
            "user@example.com",
            method=PasswordResetMethod.MAGIC_LINK,
            token="token123",
        )
        is True
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
                id=uuid4(),
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
        "app.services.user.basic_auth.UserBasicAuthService.generate_verification_link",
        lambda self: "https://api.example.com/user/verify?token=test-token",
    )
    monkeypatch.setattr(
        "app.services.user.basic_auth.logger.error",
        lambda message, extra: captured_errors.append((message, extra)),
    )

    user = UserReadModel(
        id=uuid4(),
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
        id=uuid4(),
        email="admin@example.com",
        first_name="Admin",
        last_name="User",
        phone_number="+27123456789",
        status=UserAccountStatus.ACTIVE.name_value,
        is_superuser=False,
    )
    added_user = UserReadModel(
        id=uuid4(),
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
        {
            **added_user.model_dump(mode="json"),
            "role": type("Role", (), {"name": "Viewer"})(),
        },
    )()
    company = type("Company", (), {"name": "Acme Co"})()

    service = CompanyUserService(SharedContext(db_session=object(), user=acting_user))
    monkeypatch.setattr(service.authorization, "require", lambda *args: None)
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
        company_id=uuid4(),
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
        id=uuid4(),
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
        repository.ensure_user_linked_to_company(user_id=uuid4(), company_id=uuid4())

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

    assert (
        repository.ensure_user_linked_to_company(user_id=uuid4(), company_id=uuid4())
        is True
    )


def test_user_repository_get_user_by_id_wraps_unexpected_errors(monkeypatch):
    from app.repository.user import UserRepository

    repository = UserRepository(db_session=object())

    class FailingQuery:
        def filter(self, *args, **kwargs):
            raise RuntimeError("db blew up")

    monkeypatch.setattr(repository, "_active_user_query", lambda: FailingQuery())

    with pytest.raises(AppError) as exc_info:
        repository.get_user_by_id(uuid4())

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail["message"] == UserResponseMessages.USER_NOT_FOUND.value


def test_user_repository_get_user_by_email_rehashes_plaintext_password(monkeypatch):
    from app.repository.user import UserRepository

    class FakeUser:
        id = uuid4()
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
    monkeypatch.setattr(
        repository,
        "_active_user_query",
        lambda: Mock(filter=lambda *a, **k: Mock(first=lambda: None)),
    )

    def raise_integrity(**kwargs):
        raise IntegrityError(
            "insert", {}, Exception("UNIQUE constraint failed: user.email")
        )

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
        repository.update_user(uuid4(), {"first_name": "Updated"})

    assert exc_info.value.status_code == 400
    assert (
        exc_info.value.detail["message"]
        == UserResponseMessages.USER_UPDATE_FAILED.value
    )


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
        repository.update_user_status(uuid4(), UserAccountStatus.ACTIVE.name_value)

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
        repository.increment_refresh_token_version(uuid4())

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
        repository.delete_user(uuid4())

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail["message"] == UserResponseMessages.USER_NOT_FOUND.value


def test_user_profile_service_get_user_prefers_id(monkeypatch):
    acting_user = UserReadModel(
        id=uuid4(),
        email="admin@example.com",
        first_name="Admin",
        last_name="User",
        phone_number="+27123456789",
        status=UserAccountStatus.ACTIVE.name_value,
        is_superuser=False,
    )
    service = UserProfileService(SharedContext(db_session=object(), user=acting_user))
    expected = UserReadModel(
        id=uuid4(),
        email="target@example.com",
        first_name="Target",
        last_name="User",
        phone_number="+27123456789",
        status=UserAccountStatus.ACTIVE.name_value,
        is_superuser=False,
    )
    monkeypatch.setattr(
        service.user_repository, "get_user_by_id", lambda user_id: expected
    )
    monkeypatch.setattr(
        service.user_repository,
        "get_user_by_email",
        lambda email: (_ for _ in ()).throw(
            AssertionError("email path should not be used")
        ),
    )

    result = service.get_user(user_id=expected.id, user_email="ignored@example.com")

    assert result == expected


def test_user_profile_service_get_user_raises_without_identifier():
    acting_user = UserReadModel(
        id=uuid4(),
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
        id=uuid4(),
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
        id=uuid4(),
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
    monkeypatch.setattr(
        "app.services.user.profile.hash_password",
        lambda password: f"hashed::{password}",
    )

    result = service.update_user(
        acting_user.id,
        UserUpdateModel(phone_number="011 222 3333", password="secret"),
    )

    assert result == expected
    assert captured == {
        "user_id": acting_user.id,
        "data": {"phone_number": "011 222 3333", "password": "hashed::secret"},
    }

    with pytest.raises(AppError) as exc_info:
        service.update_user(acting_user.id, UserUpdateModel())

    assert exc_info.value.status_code == 400
    assert (
        exc_info.value.detail["message"]
        == UserResponseMessages.INVALID_REQUEST_MESSAGE.value
    )


def test_user_profile_service_get_user_companies_and_delete_user(monkeypatch):
    acting_user = UserReadModel(
        id=uuid4(),
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
    service.delete_user(acting_user.id)

    assert captured["companies"] == (acting_user.id, params)
    assert captured["deleted"] == acting_user.id


def test_shared_context_safe_json_returns_scalars_unchanged():
    assert SharedContext.safe_json("plain") == "plain"


from uuid import uuid4


def test_verification_service_resend_returns_generic_success_for_unknown_email(
    monkeypatch,
):
    captured_logs = []

    class FakeUserRepository:
        def __init__(self, session):
            self.session = session

        def get_user_record_by_email(self, email):
            return None

    monkeypatch.setattr(
        "app.services.user.verification.UserRepository",
        FakeUserRepository,
    )
    monkeypatch.setattr(
        "app.services.user.verification.logger.info",
        lambda message, extra: captured_logs.append((message, extra)),
    )

    response = UserVerificationService(session=object()).resend_verification_email(
        "missing@example.com",
        server_url="https://api.example.com",
        app_name="Userverse",
        verification_required=True,
        client_ip="127.0.0.1",
    )

    assert response.message == UserResponseMessages.VERIFICATION_EMAIL_RESENT.value
    assert captured_logs[0][0] == "Verification resend requested for unknown email"


def test_verification_service_resend_skips_non_pending_accounts(monkeypatch):
    captured_logs = []
    session_user = types.SimpleNamespace(
        email="active@example.com",
        first_name="Active",
        last_name="User",
        primary_meta_data={"status": UserAccountStatus.ACTIVE.name_value},
    )

    class FakeUserRepository:
        def __init__(self, session):
            self.session = session

        def get_user_record_by_email(self, email):
            return session_user

    monkeypatch.setattr(
        "app.services.user.verification.UserRepository",
        FakeUserRepository,
    )
    monkeypatch.setattr(
        "app.services.user.verification.logger.info",
        lambda message, extra: captured_logs.append((message, extra)),
    )

    response = UserVerificationService(session=object()).resend_verification_email(
        "active@example.com",
        server_url="https://api.example.com",
        app_name="Userverse",
        verification_required=True,
        client_ip="127.0.0.1",
    )

    assert response.message == UserResponseMessages.VERIFICATION_EMAIL_RESENT.value
    assert captured_logs[0][0] == "Verification resend skipped for non-pending account"


def test_verification_service_resend_logs_dispatch_failures(monkeypatch):
    captured_errors = []
    session_user = types.SimpleNamespace(
        email="pending@example.com",
        first_name="Pending",
        last_name="User",
        primary_meta_data={
            "status": UserAccountStatus.AWAITING_VERIFICATION.name_value
        },
    )

    class FakeUserRepository:
        def __init__(self, session):
            self.session = session

        def get_user_record_by_email(self, email):
            return session_user

    monkeypatch.setattr(
        "app.services.user.verification.UserRepository",
        FakeUserRepository,
    )
    monkeypatch.setattr(
        "app.services.user.verification.JWTManager.sign_payload",
        lambda self, payload, expires_delta: "verification-token",
    )
    monkeypatch.setattr(
        "app.services.user.verification.MailService.send_template_email",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("smtp down")),
    )
    monkeypatch.setattr(
        "app.services.user.verification.logger.error",
        lambda message, extra: captured_errors.append((message, extra)),
    )

    response = UserVerificationService(session=object()).resend_verification_email(
        "pending@example.com",
        server_url="https://api.example.com/",
        app_name="Userverse",
        verification_required=True,
        client_ip="127.0.0.1",
    )

    assert response.message == UserResponseMessages.VERIFICATION_EMAIL_RESENT.value
    assert captured_errors[0][0] == "Verification email dispatch failed"
    assert captured_errors[0][1]["extra"]["error"] == "smtp down"


def test_company_service_branches_for_falsey_repository_results(monkeypatch):
    acting_user = UserReadModel(
        id=uuid4(),
        email="owner@example.com",
        first_name="Owner",
        last_name="User",
        phone_number="+27123456789",
        status=UserAccountStatus.ACTIVE.name_value,
        is_superuser=False,
    )
    context = SharedContext(db_session=object(), user=acting_user)
    service = CompanyService(context)

    monkeypatch.setattr(
        service.company_repository, "create_company", lambda payload, user: None
    )
    with pytest.raises(AppError) as exc_info:
        service.create_company(
            CompanyCreateModel(
                email="company@example.com",
                name="Acme",
                description="Desc",
                industry="Tech",
                phone_number="+27123456789",
                address=None,
            )
        )
    assert (
        exc_info.value.detail["message"]
        == CompanyResponseMessages.COMPANY_CREATION_FAILED.value
    )

    with pytest.raises(AppError) as exc_info:
        service.get_company()
    assert (
        exc_info.value.detail["message"]
        == CompanyResponseMessages.COMPANY_ID_OR_EMAIL_REQUIRED.value
    )

    monkeypatch.setattr(service.authorization, "require", lambda *args: None)
    monkeypatch.setattr(
        service.company_repository,
        "update_company",
        lambda payload, company_id, user: None,
    )
    with pytest.raises(AppError) as exc_info:
        service.update_company(CompanyUpdateModel(name="Updated"), uuid4())
    assert (
        exc_info.value.detail["message"]
        == CompanyResponseMessages.COMPANY_UPDATE_FAILED.value
    )


def test_role_service_branches_for_falsey_repository_results(monkeypatch):
    acting_user = UserReadModel(
        id=uuid4(),
        email="owner@example.com",
        first_name="Owner",
        last_name="User",
        phone_number="+27123456789",
        status=UserAccountStatus.ACTIVE.name_value,
        is_superuser=False,
    )
    context = SharedContext(db_session=object(), user=acting_user)
    service = RoleService(context)
    company_id = uuid4()

    monkeypatch.setattr(service, "_ensure_superuser", lambda: None)
    monkeypatch.setattr(RoleRepository, "update_role", lambda self, name, payload: None)
    with pytest.raises(AppError) as exc_info:
        service.update_role(
            company_id,
            "Viewer",
            RoleUpdateModel(name=None, description="Updated"),
        )
    assert (
        exc_info.value.detail["message"]
        == CompanyRoleResponseMessages.ROLE_UPDATE_FAILED.value
    )

    monkeypatch.setattr(
        RoleRepository, "create_role", lambda self, payload, created_by: None
    )
    with pytest.raises(AppError) as exc_info:
        service.create_role(
            RoleCreateModel(name="Viewer", description="Desc"), company_id
        )
    assert (
        exc_info.value.detail["message"]
        == CompanyRoleResponseMessages.ROLE_CREATION_FAILED.value
    )


def test_role_service_superuser_guard_rejects_non_superusers():
    acting_user = UserReadModel(
        id=uuid4(),
        email="owner@example.com",
        first_name="Owner",
        last_name="User",
        phone_number="+27123456789",
        status=UserAccountStatus.ACTIVE.name_value,
        is_superuser=False,
    )
    context = SharedContext(db_session=object(), user=acting_user)
    service = RoleService(context)
    company_id = uuid4()
    role_id = uuid4()
    payload = RoleCreateModel(name="Viewer", description="Read only")

    guarded_calls = [
        lambda: service.create_role(payload),
        lambda: service.update_role(
            role_id=role_id,
            payload=RoleUpdateModel(name=None, description="Updated"),
        ),
        lambda: service.delete_global_role(role_id),
        lambda: service.assign_role_to_companies(
            role_id, RoleAssignCompaniesModel(company_ids=[str(company_id)])
        ),
        lambda: service.create_role_for_company(payload, company_id),
        lambda: service.update_company_role(
            company_id,
            "Viewer",
            RoleUpdateModel(name=None, description="Updated"),
        ),
        lambda: service.delete_role(
            RoleDeleteModel(
                role_name_to_delete="Client",
                replacement_role_name="Viewer",
            ),
            company_id,
        ),
    ]

    for guarded_call in guarded_calls:
        with pytest.raises(AppError) as exc_info:
            guarded_call()
        assert exc_info.value.status_code == 403
        assert (
            exc_info.value.detail["message"]
            == CompanyRoleResponseMessages.ROLE_MANAGEMENT_FORBIDDEN.value
        )


def test_global_role_router_wrappers(monkeypatch):
    acting_user = types.SimpleNamespace(id=uuid4())
    common = types.SimpleNamespace(user=acting_user, session=object())
    role_id = uuid4()
    role = RoleReadModel(id=str(role_id), name="Viewer", description="Read only")
    paginated = PaginatedResponse[RoleReadModel](
        records=[role],
        pagination={
            "current_page": 1,
            "limit": 10,
            "total_records": 1,
            "total_pages": 1,
        },
    )

    monkeypatch.setattr(RoleService, "create_role", lambda self, payload: role)
    monkeypatch.setattr(RoleService, "get_roles", lambda self, payload: paginated)
    monkeypatch.setattr(RoleService, "update_role", lambda self, **kwargs: role)
    monkeypatch.setattr(
        RoleService,
        "delete_global_role",
        lambda self, role_id: {"message": "Role deleted"},
    )
    monkeypatch.setattr(
        RoleService,
        "assign_role_to_companies",
        lambda self, role_id, payload: {
            "role_id": str(role_id),
            "company_ids": payload.company_ids,
        },
    )

    create_response = global_roles_router.create_role_api(
        RoleCreateModel(name="Viewer", description="Read only"),
        common=common,
    )
    assert create_response.status_code == 201

    get_response = global_roles_router.get_roles_api(
        query_params=RoleQueryParamsModel(limit=10, page=1),
        common=common,
    )
    assert get_response.status_code == 200

    update_response = global_roles_router.update_role_api(
        role_id=role_id,
        payload=RoleUpdateModel(name="Viewer+", description="Updated"),
        common=common,
    )
    assert update_response.status_code == 200

    delete_response = global_roles_router.delete_role_api(
        role_id=role_id, common=common
    )
    assert delete_response.status_code == 200

    assign_response = global_roles_router.assign_role_to_companies_api(
        role_id=role_id,
        payload=RoleAssignCompaniesModel(company_ids=[str(uuid4())]),
        common=common,
    )
    assert assign_response.status_code == 201


def test_company_role_router_assignment_wrappers(monkeypatch):
    acting_user = types.SimpleNamespace(id=uuid4())
    common = types.SimpleNamespace(user=acting_user, session=object())
    company_id = uuid4()
    role_id = uuid4()
    role = RoleReadModel(id=str(role_id), name="Viewer", description="Read only")

    monkeypatch.setattr(
        RoleService, "assign_role_to_company", lambda self, company_id, role_id: role
    )
    monkeypatch.setattr(
        RoleService,
        "unassign_role",
        lambda self, company_id, role_id: {"message": "Role unassigned successfully."},
    )

    assign_response = company_roles_router.assign_role_to_company_api(
        company_id=company_id,
        role_id=role_id,
        common=common,
    )
    assert assign_response.status_code == 201

    unassign_response = company_roles_router.unassign_role_from_company_api(
        company_id=company_id,
        role_id=role_id,
        common=common,
    )
    assert unassign_response.status_code == 200


def test_role_service_happy_path_branches(monkeypatch):
    acting_user = UserReadModel(
        id=uuid4(),
        email="admin@example.com",
        first_name="Admin",
        last_name="User",
        phone_number="+27123456789",
        status=UserAccountStatus.ACTIVE.name_value,
        is_superuser=True,
    )
    context = SharedContext(db_session=object(), user=acting_user)
    service = RoleService(context)
    company_id = uuid4()
    role_id = uuid4()
    role = RoleReadModel(id=str(role_id), name="Viewer", description="Read only")

    monkeypatch.setattr(service, "_ensure_superuser", lambda: None)
    monkeypatch.setattr(service, "_ensure_company_permission", lambda *args: None)
    monkeypatch.setattr(
        RoleRepository,
        "get_roles",
        lambda self, payload: {
            "records": [{"id": role_id, "name": "Viewer", "description": "Read only"}],
            "pagination": {
                "current_page": 1,
                "limit": 10,
                "total_records": 1,
                "total_pages": 1,
            },
        },
    )
    monkeypatch.setattr(
        RoleRepository,
        "delete_role",
        lambda self, role_id, user: {"message": "deleted"},
    )
    monkeypatch.setattr(
        RoleRepository,
        "ensure_role_exists",
        lambda self, role_id: types.SimpleNamespace(id=role_id),
    )
    monkeypatch.setattr(
        RoleRepository,
        "get_role_by_name",
        lambda self, name: types.SimpleNamespace(
            id=role_id, name=name, description="Read only"
        ),
    )
    monkeypatch.setattr(
        CompanyRoleAssignmentRepository,
        "assign_role",
        lambda self, role, user: RoleReadModel(
            id=str(role.id), name="Viewer", description="Read only"
        ),
    )
    monkeypatch.setattr(
        CompanyRoleAssignmentRepository,
        "assign_role_to_companies",
        lambda self, role, payload, user: {
            "role_id": str(role.id),
            "company_ids": payload.company_ids,
        },
    )
    monkeypatch.setattr(
        CompanyRoleAssignmentRepository,
        "unassign_role",
        lambda self, role_id: {"message": "Role unassigned successfully."},
    )
    monkeypatch.setattr(
        CompanyRoleAssignmentRepository,
        "reassign_and_delete_role",
        lambda self, payload, user: {"message": "deleted", "users_reassigned": 1},
    )
    monkeypatch.setattr(
        CompanyRoleAssignmentRepository,
        "get_company_roles",
        lambda self, payload: {
            "records": [{"id": role_id, "name": "Viewer", "description": "Read only"}],
            "pagination": {
                "current_page": 1,
                "limit": 10,
                "total_records": 1,
                "total_pages": 1,
            },
        },
    )

    paginated = service.get_roles(RoleQueryParamsModel(limit=10, page=1))
    assert paginated.records[0].name == "Viewer"

    assert service.delete_global_role(role_id)["message"] == "deleted"
    assert service.assign_role_to_company(company_id, role_id).id == str(role_id)
    assert service.assign_role_to_companies(
        role_id, RoleAssignCompaniesModel(company_ids=[])
    ) == {"role_id": str(role_id), "company_ids": []}
    assert service.assign_role_to_companies(
        role_id, RoleAssignCompaniesModel(company_ids=[str(company_id)])
    ) == {"role_id": str(role_id), "company_ids": [str(company_id)]}
    assert service.create_role_for_company(
        RoleCreateModel(name="Viewer", description="Read only"),
        company_id,
    ).id == str(role_id)
    assert (
        service.unassign_role(company_id, role_id)["message"]
        == "Role unassigned successfully."
    )
    assert (
        service.delete_role(
            RoleDeleteModel(
                role_name_to_delete="Client", replacement_role_name="Viewer"
            ),
            company_id,
        )["users_reassigned"]
        == 1
    )
    company_roles = service.get_company_roles(
        RoleQueryParamsModel(limit=10, page=1),
        company_id,
    )
    assert company_roles.records[0].id == str(role_id)


def test_role_service_update_role_additional_falsey_paths(monkeypatch):
    acting_user = UserReadModel(
        id=uuid4(),
        email="admin@example.com",
        first_name="Admin",
        last_name="User",
        phone_number="+27123456789",
        status=UserAccountStatus.ACTIVE.name_value,
        is_superuser=False,
    )
    context = SharedContext(db_session=object(), user=acting_user)
    service = RoleService(context)
    company_id = uuid4()

    monkeypatch.setattr(service, "_ensure_superuser", lambda: None)
    monkeypatch.setattr(
        CompanyRoleAssignmentRepository,
        "update_company_role",
        lambda self, name, payload: None,
    )

    with pytest.raises(AppError) as exc_info:
        service.update_company_role(
            company_id,
            "Viewer",
            RoleUpdateModel(name=None, description="Updated"),
        )
    assert (
        exc_info.value.detail["message"]
        == CompanyRoleResponseMessages.ROLE_UPDATE_FAILED.value
    )


def test_role_service_update_role_keyword_success(monkeypatch):
    acting_user = UserReadModel(
        id=uuid4(),
        email="admin@example.com",
        first_name="Admin",
        last_name="User",
        phone_number="+27123456789",
        status=UserAccountStatus.ACTIVE.name_value,
        is_superuser=False,
    )
    context = SharedContext(db_session=object(), user=acting_user)
    service = RoleService(context)
    role = RoleReadModel(id=str(uuid4()), name="Viewer", description="Updated")

    monkeypatch.setattr(service, "_ensure_superuser", lambda: None)
    monkeypatch.setattr(
        RoleRepository, "update_role", lambda self, role_id, payload: role
    )

    assert (
        service.update_role(
            role_id=uuid4(), payload=RoleUpdateModel(name=None, description="Updated")
        )
        == role
    )

    monkeypatch.setattr(
        RoleRepository, "update_role", lambda self, role_id, payload: None
    )
    with pytest.raises(AppError) as exc_info:
        service.update_role(uuid4(), RoleUpdateModel(name=None, description="Updated"))
    assert (
        exc_info.value.detail["message"]
        == CompanyRoleResponseMessages.ROLE_UPDATE_FAILED.value
    )


def test_company_repository_wraps_integrity_error(monkeypatch):
    repository = CompanyRepository(Mock())
    repository.db_session.rollback = Mock()
    monkeypatch.setattr(
        repository,
        "_get_company_record_by_email",
        lambda email: None,
    )

    from sqlalchemy.exc import IntegrityError

    def _raise_integrity(**kwargs):
        raise IntegrityError("insert", {}, Exception("duplicate"))

    monkeypatch.setattr(repository, "create", _raise_integrity)

    with pytest.raises(AppError) as exc_info:
        repository.create_company(
            CompanyCreateModel(
                email="company@example.com",
                name="Acme",
                description="Desc",
                industry="Tech",
                phone_number="+27123456789",
                address=None,
            ),
            created_by=types.SimpleNamespace(email="owner@example.com"),
        )

    assert (
        exc_info.value.detail["message"]
        == CompanyResponseMessages.COMPANY_ALREADY_EXISTS.value
    )
    repository.db_session.rollback.assert_called_once()


def test_company_repository_missing_record_branches():
    repository = CompanyRepository(Mock())
    repository._get_company_record_by_email = lambda email: None
    repository._get_company_record_by_id = lambda company_id: None

    with pytest.raises(AppError) as exc_info:
        repository.get_company_by_email("missing@example.com")
    assert (
        exc_info.value.detail["message"]
        == CompanyResponseMessages.COMPANY_NOT_FOUND.value
    )

    with pytest.raises(AppError) as exc_info:
        repository.update_company(CompanyUpdateModel(name="Updated"), uuid4(), object())
    assert (
        exc_info.value.detail["message"]
        == CompanyResponseMessages.COMPANY_UPDATE_FAILED.value
    )

    with pytest.raises(AppError) as exc_info:
        repository.delete_company(uuid4())
    assert (
        exc_info.value.detail["message"]
        == CompanyResponseMessages.COMPANY_NOT_FOUND.value
    )


def test_role_repository_error_branches(monkeypatch):
    repository = RoleRepository(company_id=uuid4(), session=Mock())
    monkeypatch.setattr(
        repository,
        "paginate",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("bad query")),
    )
    with pytest.raises(AppError) as exc_info:
        repository.get_roles(RoleQueryParamsModel(limit=10, page=1))
    assert (
        exc_info.value.detail["message"]
        == CompanyRoleResponseMessages.ROLE_NOT_FOUND.value
    )

    monkeypatch.setattr(repository, "get_role_record", lambda role_name: None)
    with pytest.raises(AppError) as exc_info:
        repository.ensure_role_belongs_to_company("Missing")
    assert (
        exc_info.value.detail["message"]
        == CompanyUserResponseMessages.ADD_USER_FAILED.value
    )

    deleted_by = UserReadModel(
        id=uuid4(),
        email="admin@example.com",
        first_name="Admin",
        last_name="User",
        phone_number="+27123456789",
        status=UserAccountStatus.ACTIVE.name_value,
        is_superuser=False,
    )
    with pytest.raises(AppError) as exc_info:
        repository.delete_role(
            payload=types.SimpleNamespace(
                role_name_to_delete="Missing",
                replacement_role_name="Viewer",
            ),
            deleted_by=deleted_by,
        )
    assert (
        exc_info.value.detail["message"]
        == CompanyRoleResponseMessages.ROLE_UPDATE_FAILED.value
    )


def test_lifespan_logs_startup_and_shutdown(monkeypatch):
    events = []
    monkeypatch.setattr(
        main_module.logger, "info", lambda message: events.append(message)
    )
    monkeypatch.setattr(main_module, "get_engine", lambda: "engine")

    async def _run():
        async with main_module.lifespan(Mock()):
            events.append("inside")

    import asyncio

    asyncio.run(_run())
    assert events == [
        "Userverse API starting up",
        "inside",
        "Userverse API shutting down",
    ]


def test_main_module_executes_click_entrypoint(monkeypatch):
    called = []
    monkeypatch.setattr(
        "click.core.Command.main",
        lambda self, *args, **kwargs: called.append(self.name),
    )
    runpy.run_module("app.main", run_name="__main__")
    assert called


def test_exceptions_module_reuses_counter_from_registry(monkeypatch):
    import prometheus_client

    fake_counter = object()
    fake_registry = types.SimpleNamespace(
        _names_to_collectors={"unhandled_exceptions_total": fake_counter}
    )
    original_counter = prometheus_client.Counter
    original_registry = prometheus_client.REGISTRY

    monkeypatch.setattr(
        "prometheus_client.Counter",
        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("dup")),
    )
    monkeypatch.setattr("prometheus_client.REGISTRY", fake_registry)

    reloaded = importlib.reload(exceptions_module)
    try:
        assert reloaded.UNHANDLED_EXCEPTIONS is fake_counter
    finally:
        monkeypatch.setattr("prometheus_client.Counter", original_counter)
        monkeypatch.setattr("prometheus_client.REGISTRY", original_registry)
        importlib.reload(exceptions_module)


def test_unwrap_exception_handles_context_and_missing_base_exception_group(monkeypatch):
    inner = ValueError("inner")
    outer = RuntimeError("outer")
    outer.__context__ = inner

    root, trail = exceptions_module.unwrap_exception(outer)
    assert root is inner
    assert trail == ["RuntimeError", "ValueError"]

    builtins_without_group = dict(exceptions_module.__dict__["__builtins__"])
    builtins_without_group.pop("BaseExceptionGroup", None)
    monkeypatch.setitem(
        exceptions_module.__dict__, "__builtins__", builtins_without_group
    )

    same_root, same_trail = exceptions_module.unwrap_exception(RuntimeError("plain"))
    assert isinstance(same_root, RuntimeError)
    assert same_trail == ["RuntimeError"]
