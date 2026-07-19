import importlib
from pathlib import Path
from textwrap import dedent
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

import app.services.mailer as mailer_module
from app.configs import Settings, _SettingsProxy
from app.models.phone_number import validate_phone_number_format
from app.models.tags import UserverseApiTag
from app.models.user.account_status import UserAccountStatus
from app.models.user.password import OTPValidationRequest, PasswordResetRequest
from app.utils.hash_password import UnknownHashError, verify_password
from app.utils.parsing import normalize_origins
from app.utils.project_metadata import load_project_defaults


def test_normalize_origins_handles_supported_shapes():
    assert normalize_origins(None) == []
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
        dedent(
            """
            [project]
            name = "customverse"
            version = "1.2.3"
            description = "Custom service"

            [project.urls]
            Repository = "https://example.com/repo"
            Documentation = "https://example.com/docs"
            """
        ).strip(),
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
        _env_file=None,
    )
    assert fallback_settings.DATABASE_URL == "sqlite:///./review.db"
    assert fallback_settings.PROJECT_ROOT.name == "userverse"


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
    assert validate_phone_number_format("+27123456789") == "+27123456789"
    assert validate_phone_number_format("011 222 3333") == "011 222 3333"

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
