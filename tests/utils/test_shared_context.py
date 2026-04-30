from datetime import date, datetime
from decimal import Decimal

import pytest

from app.models.user.account_status import UserAccountStatus
from app.models.user.user import UserReadModel
from app.utils.shared_context import SharedContext


def _build_user(*, status: str = "Active") -> UserReadModel:
    return UserReadModel(
        id=1,
        first_name="Jane",
        last_name="Doe",
        email="jane@example.com",
        phone_number="1234567890",
        status=status,
        is_superuser=False,
    )


def test_shared_context_enforces_active_status():
    with pytest.raises(ValueError, match="Account is not active"):
        SharedContext(
            db_session=object(),
            user=_build_user(status=UserAccountStatus.SUSPENDED.name_value),
            enforce_status_check=True,
        )


def test_shared_context_user_helpers_and_log_context():
    context = SharedContext(db_session=object(), user=_build_user())

    assert context.get_user_email() == "jane@example.com"
    assert context.get_user().first_name == "Jane"
    assert context.log_context() == {"user_email": "jane@example.com"}


def test_shared_context_logging_helpers(monkeypatch):
    info_calls = []
    error_calls = []
    monkeypatch.setattr(
        "app.utils.shared_context.logger.info", lambda *args: info_calls.append(args)
    )
    monkeypatch.setattr(
        "app.utils.shared_context.logger.error", lambda *args: error_calls.append(args)
    )

    context = SharedContext(db_session=object(), user=_build_user())
    context.log_info("created")
    context.log_error("failed")

    assert info_calls == [("user_email=%s, message=%s", "jane@example.com", "created")]
    assert error_calls == [("user_email=%s, message=%s", "jane@example.com", "failed")]


def test_shared_context_safe_json_handles_nested_values():
    now = datetime(2026, 1, 2, 3, 4, 5)
    payload = {
        "today": date(2026, 1, 2),
        "created_at": now,
        "amount": Decimal("2.5"),
        "items": [Decimal("1.0"), {"when": now}],
    }

    converted = SharedContext.safe_json(payload)

    assert converted == {
        "today": "2026-01-02",
        "created_at": now.isoformat(),
        "amount": 2.5,
        "items": [1.0, {"when": now.isoformat()}],
    }
