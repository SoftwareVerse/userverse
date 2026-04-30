import pytest

from app.utils.app_error import AppError


def test_app_error_uses_fallback_error_message_when_error_missing():
    error = AppError(log_error=False, depth=0)

    assert error.status_code == 400
    assert error.detail["message"] == "Request failed, please try again."
    assert "An error occurred" in error.detail["error"]


def test_get_caller_details_with_excessive_depth_returns_empty_fields():
    details = AppError.get_caller_details(10_000)

    assert details == {"file": "", "line": "", "function": ""}


def test_log_exception_emits_stacktrace(monkeypatch):
    messages = []
    monkeypatch.setattr("app.utils.app_error.logger.error", messages.append)

    error = AppError(log_error=False)
    try:
        raise RuntimeError("boom")
    except RuntimeError:
        error.log_exception()

    assert messages
    assert messages[0].startswith("StackTrace:")
