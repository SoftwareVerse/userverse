import socket
import smtplib
from unittest.mock import MagicMock, patch

import pytest

from app.configs import CorsSettings, EmailSettings, JwtSettings, RuntimeSettings
from app.utils.email.sender import deliver_email, send_email


def _runtime_settings(
    environment: str = "prod", email: dict | None = None
) -> RuntimeSettings:
    email = email or {}
    return RuntimeSettings(
        environment=environment,
        database_url="sqlite:///test.db",
        server_url="http://localhost:8000",
        cor_origins=CorsSettings(),
        jwt=JwtSettings(),
        email=EmailSettings(
            host=email.get("HOST"),
            port=email.get("PORT"),
            username=email.get("USERNAME"),
            password=email.get("PASSWORD"),
            use_ssl=email.get("USE_SSL"),
            use_starttls=email.get("USE_STARTTLS"),
        ),
        name="userverse",
        version="0.1.0",
        description="test",
    )


def test_send_email_calls_deliver_email():
    with patch("app.utils.email.sender.deliver_email") as mock_deliver:
        send_email("to@example.com", "Subject", "<p>body</p>")

    mock_deliver.assert_called_once_with(
        "to@example.com", "Subject", "<p>body</p>", reason="rendered"
    )


def test_send_email_uses_custom_reason():
    with patch("app.utils.email.sender.deliver_email") as mock_deliver:
        send_email("to@example.com", "Subject", "<p>body</p>", reason="password_reset")

    mock_deliver.assert_called_once_with(
        "to@example.com", "Subject", "<p>body</p>", reason="password_reset"
    )


def test_send_email_default_reason_when_empty_string():
    with patch("app.utils.email.sender.deliver_email") as mock_deliver:
        send_email("to@example.com", "Subject", "<p>body</p>")

    assert mock_deliver.call_args.kwargs["reason"] == "rendered"


def test_deliver_email_in_test_environment(capfd):
    fake_settings = _runtime_settings(environment="test_environment")

    with patch(
        "app.utils.email.sender.get_settings", return_value=fake_settings
    ):
        deliver_email(
            "test@example.com", "Test Subject", "<h1>Hello</h1><p>This is a test</p>"
        )
        out, _ = capfd.readouterr()
        assert "Hello" in out
        assert "This is a test" in out


def test_deliver_email_missing_username(capfd):
    fake_settings = _runtime_settings(
        email={"PASSWORD": "pass", "HOST": "smtp.test.com", "PORT": 465}
    )

    with patch(
        "app.utils.email.sender.get_settings", return_value=fake_settings
    ):
        deliver_email("to@example.com", "Subject", "<h1>Missing</h1><p>User field</p>")
        out, _ = capfd.readouterr()
        assert "Email config not available" in out
        assert "User field" in out


def test_deliver_email_missing_password(capfd):
    fake_settings = _runtime_settings(
        email={"USERNAME": "user@test.com", "HOST": "smtp.test.com", "PORT": 465}
    )

    with patch(
        "app.utils.email.sender.get_settings", return_value=fake_settings
    ):
        deliver_email("to@example.com", "Subject", "<h1>Missing</h1><p>Password</p>")
        out, _ = capfd.readouterr()
        assert "Email config not available" in out
        assert "Password" in out


def test_deliver_email_missing_host_or_port(capfd):
    fake_settings = _runtime_settings(
        email={"USERNAME": "user@test.com", "PASSWORD": "secure"}
    )

    with patch(
        "app.utils.email.sender.get_settings", return_value=fake_settings
    ):
        deliver_email("to@example.com", "Subject", "<h1>Missing</h1><p>SMTP config</p>")
        out, _ = capfd.readouterr()
        assert "Email config not available" in out
        assert "SMTP config" in out


def test_deliver_email_success():
    fake_settings = _runtime_settings(
        email={
            "USERNAME": "user@test.com",
            "PASSWORD": "secure",
            "HOST": "smtp.test.com",
            "PORT": 465,
        }
    )

    with patch(
        "app.utils.email.sender.get_settings", return_value=fake_settings
    ):
        with patch("smtplib.SMTP_SSL") as mock_smtp_ssl:
            mock_server = MagicMock()
            mock_smtp_ssl.return_value.__enter__.return_value = mock_server

            deliver_email("to@example.com", "Subject", "<p>test</p>")

            mock_server.login.assert_called_once_with("user@test.com", "secure")
            mock_server.send_message.assert_called_once()


def test_deliver_email_dns_failure(capfd):
    fake_settings = _runtime_settings(
        email={
            "USERNAME": "user@test.com",
            "PASSWORD": "secure",
            "HOST": "smtp.test.com",
            "PORT": 465,
        }
    )

    with patch(
        "app.utils.email.sender.get_settings", return_value=fake_settings
    ):
        with patch("smtplib.SMTP_SSL") as mock_smtp_ssl:
            mock_smtp_ssl.side_effect = socket.gaierror(
                socket.EAI_NONAME, "Name or service not known"
            )

            deliver_email("to@example.com", "Subject", "<p>test</p>")

            out, _ = capfd.readouterr()
            assert "Unable to reach SMTP host smtp.test.com" in out
            assert "Subject: Subject" in out
            assert "test" in out


def test_deliver_email_socket_timeout():
    fake_settings = _runtime_settings(
        email={
            "USERNAME": "user@test.com",
            "PASSWORD": "secure",
            "HOST": "smtp.test.com",
            "PORT": 465,
        }
    )

    with patch(
        "app.utils.email.sender.get_settings", return_value=fake_settings
    ):
        with patch("smtplib.SMTP_SSL") as mock_smtp_ssl:
            mock_smtp_ssl.side_effect = socket.timeout("Connection timed out")

            with pytest.raises(socket.timeout):
                deliver_email("to@example.com", "Subject", "<p>test</p>")


def test_deliver_email_smtp_server_disconnected():
    fake_settings = _runtime_settings(
        email={
            "USERNAME": "user@test.com",
            "PASSWORD": "secure",
            "HOST": "smtp.test.com",
            "PORT": 465,
        }
    )

    with patch(
        "app.utils.email.sender.get_settings", return_value=fake_settings
    ):
        with patch("smtplib.SMTP_SSL") as mock_smtp_ssl:
            mock_smtp_ssl.side_effect = smtplib.SMTPServerDisconnected(
                "Server disconnected"
            )

            with pytest.raises(smtplib.SMTPServerDisconnected):
                deliver_email("to@example.com", "Subject", "<p>test</p>")


def test_deliver_email_smtp_exception():
    fake_settings = _runtime_settings(
        email={
            "USERNAME": "user@test.com",
            "PASSWORD": "secure",
            "HOST": "smtp.test.com",
            "PORT": 465,
        }
    )

    with patch(
        "app.utils.email.sender.get_settings", return_value=fake_settings
    ):
        with patch("smtplib.SMTP_SSL") as mock_smtp_ssl:
            mock_server = MagicMock()
            mock_smtp_ssl.return_value.__enter__.return_value = mock_server
            mock_server.login.side_effect = smtplib.SMTPAuthenticationError(
                535, "Authentication failed"
            )

            with pytest.raises(smtplib.SMTPException):
                deliver_email("to@example.com", "Subject", "<p>test</p>")


def test_deliver_email_general_exception():
    fake_settings = _runtime_settings(
        email={
            "USERNAME": "user@test.com",
            "PASSWORD": "secure",
            "HOST": "smtp.test.com",
            "PORT": 465,
        }
    )

    with patch(
        "app.utils.email.sender.get_settings", return_value=fake_settings
    ):
        with patch("smtplib.SMTP_SSL") as mock_smtp_ssl:
            mock_server = MagicMock()
            mock_smtp_ssl.return_value.__enter__.return_value = mock_server
            mock_server.send_message.side_effect = Exception("Unexpected error")

            with pytest.raises(Exception):
                deliver_email("to@example.com", "Subject", "<p>test</p>")
