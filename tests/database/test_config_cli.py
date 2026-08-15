from click.testing import CliRunner

from app.cli.admin import cli

runner = CliRunner()


def _invoke(**environment):
    defaults = {
        "ENVIRONMENT": "development",
        "TESTING": "false",
        "DATABASE_URL": "sqlite:///development.db",
        "JWT_SECRET": "development-secret",
        "EMAIL_SSL": "false",
        "EMAIL_TLS": "false",
    }
    defaults.update(environment)
    return runner.invoke(cli, ["config-check"], env=defaults)


def test_config_check_accepts_development_sqlite():
    result = _invoke()

    assert result.exit_code == 0
    assert "Configuration is valid for development" in result.output
    assert "sqlite:///development.db" in result.output


def test_config_check_accepts_production_postgresql_and_hides_password():
    result = _invoke(
        ENVIRONMENT="production",
        DATABASE_URL="postgresql+psycopg2://user:private@db:5432/userverse",
        JWT_SECRET="production-secret",
    )

    assert result.exit_code == 0
    assert "postgresql+psycopg2://user:***@db:5432/userverse" in result.output
    assert "private" not in result.output


def test_config_check_rejects_invalid_settings():
    result = _invoke(ENVIRONMENT="production", JWT_SECRET="secret1234")

    assert result.exit_code == 1
    assert "Invalid configuration" in result.output


def test_config_check_rejects_invalid_database_url():
    result = _invoke(DATABASE_URL="not a url")

    assert result.exit_code == 1
    assert "not a valid SQLAlchemy URL" in result.output


def test_config_check_rejects_unsupported_database():
    result = _invoke(DATABASE_URL="oracle://user:password@db/service")

    assert result.exit_code == 1
    assert "must use PostgreSQL, MySQL" in result.output


def test_config_check_rejects_production_sqlite():
    result = _invoke(ENVIRONMENT="production", JWT_SECRET="production-secret")

    assert result.exit_code == 1
    assert "SQLite is supported only" in result.output


def test_config_check_rejects_conflicting_email_security():
    result = _invoke(EMAIL_SSL="true", EMAIL_TLS="true")

    assert result.exit_code == 1
    assert "cannot both be enabled" in result.output
