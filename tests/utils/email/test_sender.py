import socket
import smtplib
import pytest
from unittest.mock import patch, MagicMock
from app.utils.email.sender import send_email


def test_send_email_in_test_environment(capfd):
    """Should print email body in plain text when environment is test"""
    fake_config = {"environment": "test_environment", "email": {}}

    with patch(
        "app.utils.config.loader.ConfigLoader.get_config", return_value=fake_config
    ):
        send_email(
            "test@example.com", "Test Subject", "<h1>Hello</h1><p>This is a test</p>"
        )
        out, _ = capfd.readouterr()
        assert "Hello" in out
        assert "This is a test" in out


def test_send_email_missing_username(capfd):
    """Should print fallback text if username is missing"""
    fake_config = {
        "environment": "prod",
        "email": {"PASSWORD": "pass", "HOST": "smtp.test.com", "PORT": 465},
    }

    with patch(
        "app.utils.config.loader.ConfigLoader.get_config", return_value=fake_config
    ):
        send_email("to@example.com", "Subject", "<h1>Missing</h1><p>User field</p>")
        out, _ = capfd.readouterr()
        assert "Email config not available" in out
        assert "User field" in out


def test_send_email_missing_password(capfd):
    """Should print fallback text if password is missing"""
    fake_config = {
        "environment": "prod",
        "email": {"USERNAME": "user@test.com", "HOST": "smtp.test.com", "PORT": 465},
    }

    with patch(
        "app.utils.config.loader.ConfigLoader.get_config", return_value=fake_config
    ):
        send_email("to@example.com", "Subject", "<h1>Missing</h1><p>Password</p>")
        out, _ = capfd.readouterr()
        assert "Email config not available" in out
        assert "Password" in out


def test_send_email_missing_host_or_port(capfd):
    """Should print fallback text if host or port is missing"""
    fake_config = {
        "environment": "prod",
        "email": {"USERNAME": "user@test.com", "PASSWORD": "secure"},
    }

    with patch(
        "app.utils.config.loader.ConfigLoader.get_config", return_value=fake_config
    ):
        send_email("to@example.com", "Subject", "<h1>Missing</h1><p>SMTP config</p>")
        out, _ = capfd.readouterr()
        assert "Email config not available" in out
        assert "SMTP config" in out


def test_send_email_success():
    """Should send email successfully with full config using SMTP_SSL"""
    fake_config = {
        "environment": "prod",
        "email": {
            "USERNAME": "user@test.com",
            "PASSWORD": "secure",
            "HOST": "smtp.test.com",
            "PORT": 465,  # Standard port for SMTP_SSL
        },
    }

    with patch(
        "app.utils.config.loader.ConfigLoader.get_config", return_value=fake_config
    ):
        with patch("smtplib.SMTP_SSL") as mock_smtp_ssl:
            mock_server = MagicMock()
            mock_smtp_ssl.return_value.__enter__.return_value = mock_server

            send_email("to@example.com", "Subject", "<p>test</p>")

            # No starttls for SMTP_SSL
            mock_server.login.assert_called_once_with("user@test.com", "secure")
            mock_server.send_message.assert_called_once()


def test_send_email_dns_failure(capfd):
    """Should show plain text when SMTP host cannot be resolved"""
    fake_config = {
        "environment": "prod",
        "email": {
            "USERNAME": "user@test.com",
            "PASSWORD": "secure",
            "HOST": "smtp.test.com",
            "PORT": 465,
        },
    }

    with patch(
        "app.utils.config.loader.ConfigLoader.get_config", return_value=fake_config
    ):
        with patch("smtplib.SMTP_SSL") as mock_smtp_ssl:
            mock_smtp_ssl.side_effect = socket.gaierror(
                socket.EAI_NONAME, "Name or service not known"
            )

            send_email("to@example.com", "Subject", "<p>test</p>")

            out, _ = capfd.readouterr()
            assert "Unable to reach SMTP host smtp.test.com" in out
            assert "Subject: Subject" in out
            assert "test" in out


def test_send_email_socket_timeout():
    """Should log and re-raise socket timeout exceptions"""
    fake_config = {
        "environment": "prod",
        "email": {
            "USERNAME": "user@test.com",
            "PASSWORD": "secure",
            "HOST": "smtp.test.com",
            "PORT": 465,
        },
    }

    with patch(
        "app.utils.config.loader.ConfigLoader.get_config", return_value=fake_config
    ):
        with patch("smtplib.SMTP_SSL") as mock_smtp_ssl:
            mock_smtp_ssl.side_effect = socket.timeout("Connection timed out")

            with pytest.raises(socket.timeout):
                send_email("to@example.com", "Subject", "<p>test</p>")


def test_send_email_smtp_server_disconnected():
    """Should log and re-raise SMTP server disconnected exceptions"""
    fake_config = {
        "environment": "prod",
        "email": {
            "USERNAME": "user@test.com",
            "PASSWORD": "secure",
            "HOST": "smtp.test.com",
            "PORT": 465,
        },
    }

    with patch(
        "app.utils.config.loader.ConfigLoader.get_config", return_value=fake_config
    ):
        with patch("smtplib.SMTP_SSL") as mock_smtp_ssl:
            mock_smtp_ssl.side_effect = smtplib.SMTPServerDisconnected(
                "Server disconnected"
            )

            with pytest.raises(smtplib.SMTPServerDisconnected):
                send_email("to@example.com", "Subject", "<p>test</p>")


def test_send_email_smtp_exception():
    """Should log and re-raise general SMTP exceptions"""
    fake_config = {
        "environment": "prod",
        "email": {
            "USERNAME": "user@test.com",
            "PASSWORD": "secure",
            "HOST": "smtp.test.com",
            "PORT": 465,
        },
    }

    with patch(
        "app.utils.config.loader.ConfigLoader.get_config", return_value=fake_config
    ):
        with patch("smtplib.SMTP_SSL") as mock_smtp_ssl:
            mock_server = MagicMock()
            mock_smtp_ssl.return_value.__enter__.return_value = mock_server
            mock_server.login.side_effect = smtplib.SMTPAuthenticationError(
                535, "Authentication failed"
            )

            with pytest.raises(smtplib.SMTPException):
                send_email("to@example.com", "Subject", "<p>test</p>")


def test_send_email_general_exception():
    """Should log and re-raise any other exceptions"""
    fake_config = {
        "environment": "prod",
        "email": {
            "USERNAME": "user@test.com",
            "PASSWORD": "secure",
            "HOST": "smtp.test.com",
            "PORT": 465,
        },
    }

    with patch(
        "app.utils.config.loader.ConfigLoader.get_config", return_value=fake_config
    ):
        with patch("smtplib.SMTP_SSL") as mock_smtp_ssl:
            mock_server = MagicMock()
            mock_smtp_ssl.return_value.__enter__.return_value = mock_server
            mock_server.send_message.side_effect = Exception("Unexpected error")

            with pytest.raises(Exception):
                send_email("to@example.com", "Subject", "<p>test</p>")
