import socket
import smtplib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.jobs.bus import JobType
from app.utils.email.sender import deliver_email, send_email


def test_send_email_enqueues_when_bus_available():
    mock_bus = MagicMock()

    with patch("app.utils.email.sender.get_bus", return_value=mock_bus):
        send_email("to@example.com", "Subject", "<p>body</p>")

    mock_bus.enqueue.assert_called_once()
    job_type, payload = mock_bus.enqueue.call_args[0]
    assert job_type is JobType.EMAIL_SEND
    assert payload["to"] == "to@example.com"
    assert payload["reason"] == "rendered"
    assert payload["context"]["subject"] == "Subject"
    assert payload["context"]["html_body"] == "<p>body</p>"


def test_send_email_falls_back_when_bus_missing():
    with patch("app.utils.email.sender.get_bus", return_value=None), patch(
        "app.utils.email.sender.deliver_email"
    ) as mock_deliver:
        send_email("to@example.com", "Subject", "<p>body</p>")

    mock_deliver.assert_called_once_with("to@example.com", "Subject", "<p>body</p>")


def test_send_email_falls_back_on_enqueue_failure():
    mock_bus = MagicMock()
    mock_bus.enqueue.side_effect = RuntimeError("bus closed")

    with patch("app.utils.email.sender.get_bus", return_value=mock_bus), patch(
        "app.utils.email.sender.deliver_email"
    ) as mock_deliver:
        send_email("to@example.com", "Subject", "<p>body</p>")

    mock_deliver.assert_called_once()


def test_deliver_email_in_test_environment(capfd):
    fake_config = {"environment": "test_environment", "email": {}}

    with patch(
        "app.utils.config.loader.ConfigLoader.get_config", return_value=fake_config
    ):
        deliver_email(
            "test@example.com", "Test Subject", "<h1>Hello</h1><p>This is a test</p>"
        )
        out, _ = capfd.readouterr()
        assert "Hello" in out
        assert "This is a test" in out


def test_deliver_email_missing_username(capfd):
    fake_config = {
        "environment": "prod",
        "email": {"PASSWORD": "pass", "HOST": "smtp.test.com", "PORT": 465},
    }

    with patch(
        "app.utils.config.loader.ConfigLoader.get_config", return_value=fake_config
    ):
        deliver_email("to@example.com", "Subject", "<h1>Missing</h1><p>User field</p>")
        out, _ = capfd.readouterr()
        assert "Email config not available" in out
        assert "User field" in out


def test_deliver_email_missing_password(capfd):
    fake_config = {
        "environment": "prod",
        "email": {"USERNAME": "user@test.com", "HOST": "smtp.test.com", "PORT": 465},
    }

    with patch(
        "app.utils.config.loader.ConfigLoader.get_config", return_value=fake_config
    ):
        deliver_email("to@example.com", "Subject", "<h1>Missing</h1><p>Password</p>")
        out, _ = capfd.readouterr()
        assert "Email config not available" in out
        assert "Password" in out


def test_deliver_email_missing_host_or_port(capfd):
    fake_config = {
        "environment": "prod",
        "email": {"USERNAME": "user@test.com", "PASSWORD": "secure"},
    }

    with patch(
        "app.utils.config.loader.ConfigLoader.get_config", return_value=fake_config
    ):
        deliver_email("to@example.com", "Subject", "<h1>Missing</h1><p>SMTP config</p>")
        out, _ = capfd.readouterr()
        assert "Email config not available" in out
        assert "SMTP config" in out


def test_deliver_email_success():
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

            deliver_email("to@example.com", "Subject", "<p>test</p>")

            mock_server.login.assert_called_once_with("user@test.com", "secure")
            mock_server.send_message.assert_called_once()


def test_deliver_email_dns_failure(capfd):
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

            deliver_email("to@example.com", "Subject", "<p>test</p>")

            out, _ = capfd.readouterr()
            assert "Unable to reach SMTP host smtp.test.com" in out
            assert "Subject: Subject" in out
            assert "test" in out


def test_deliver_email_socket_timeout():
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
                deliver_email("to@example.com", "Subject", "<p>test</p>")


def test_deliver_email_smtp_server_disconnected():
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
                deliver_email("to@example.com", "Subject", "<p>test</p>")


def test_deliver_email_smtp_exception():
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
                deliver_email("to@example.com", "Subject", "<p>test</p>")


def test_deliver_email_general_exception():
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
                deliver_email("to@example.com", "Subject", "<p>test</p>")
