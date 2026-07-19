from datetime import timedelta

import pytest

from app.configs import settings
from app.api.security.jwt import JWTManager
from app.models.user.response_messages import UserResponseMessages
from app.repository.database.session_manager import DatabaseSessionManager
from app.repository.database.tables import User
from app.utils.rate_limiter import VERIFICATION_EMAIL_RATE_LIMITER
from tests.utils.basic_auth import get_basic_auth_header


def _verification_token(email: str, token_type: str = "verification") -> str:
    return JWTManager().sign_payload(
        {"sub": email, "type": token_type},
        expires_delta=timedelta(minutes=60),
    )


def _user_status(email: str) -> str | None:
    session = DatabaseSessionManager().session_object()
    try:
        user = session.query(User).filter_by(email=email.lower()).first()
        if not user:
            return None
        return (user.primary_meta_data or {}).get("status")
    finally:
        session.close()


@pytest.fixture(autouse=True)
def reset_verification_email_rate_limiters():
    VERIFICATION_EMAIL_RATE_LIMITER.reset()
    yield
    VERIFICATION_EMAIL_RATE_LIMITER.reset()


def test_verify_user_account_activates_user(client):
    email = "verify-target@email.com"
    password = "verifyPass123"
    original_setting = settings.REQUIRE_EMAIL_VERIFICATION
    try:
        settings.REQUIRE_EMAIL_VERIFICATION = True
        create_response = client.post(
            "/user/create",
            json={
                "first_name": "Verify",
                "last_name": "Target",
                "phone_number": "+27123456789",
            },
            headers=get_basic_auth_header(email, password),
        )

        assert create_response.status_code == 201

        response = client.get(f"/user/verify?token={_verification_token(email)}")

        assert response.status_code == 201
        assert (
            response.json()["message"]
            == UserResponseMessages.USER_ACCOUNT_VERIFIED.value
        )
        assert _user_status(email) == "Active"
    finally:
        settings.REQUIRE_EMAIL_VERIFICATION = original_setting


def test_verify_user_account_is_idempotent_for_active_user(
    client, seed_verified_users, test_user_data
):
    email = test_user_data["user_one"]["email"]

    response = client.get(f"/user/verify?token={_verification_token(email)}")

    assert response.status_code == 201
    assert (
        response.json()["message"]
        == UserResponseMessages.USER_ACCOUNT_ALREADY_ACTIVE.value
    )


def test_verify_user_account_rejects_wrong_token_type(client, seed_users, test_user_data):
    email = test_user_data["user_two"]["email"]

    response = client.get(f"/user/verify?token={_verification_token(email, 'refresh')}")

    assert response.status_code == 403
    assert response.json()["detail"]["message"] == "Invalid token"


def test_resend_verification_email_by_email_without_authentication(
    client, monkeypatch
):
    sent_messages = []
    monkeypatch.setattr(
        "app.services.user.verification.MailService.send_template_email",
        lambda **kwargs: sent_messages.append(kwargs),
    )

    email = "resend-target@email.com"
    original_setting = settings.REQUIRE_EMAIL_VERIFICATION
    try:
        settings.REQUIRE_EMAIL_VERIFICATION = True
        create_response = client.post(
            "/user/create",
            json={
                "first_name": "Resend",
                "last_name": "Target",
                "phone_number": "+27123456789",
            },
            headers=get_basic_auth_header(email, "verifyPass123"),
        )
        assert create_response.status_code == 201

        response = client.post(
            "/user/resend-verification",
            json={"email": email},
        )

        assert response.status_code == 200
        assert (
            response.json()["message"]
            == UserResponseMessages.VERIFICATION_EMAIL_RESENT.value
        )
        assert sent_messages
        assert sent_messages[0]["to"] == email
    finally:
        settings.REQUIRE_EMAIL_VERIFICATION = original_setting


def test_resend_verification_email_skips_verified_user(
    client, monkeypatch, test_user_data, seed_verified_users
):
    sent_messages = []
    monkeypatch.setattr(
        "app.services.user.verification.MailService.send_template_email",
        lambda **kwargs: sent_messages.append(kwargs),
    )

    response = client.post(
        "/user/resend-verification",
        json={"email": test_user_data["user_one"]["email"]},
    )

    assert response.status_code == 200
    assert (
        response.json()["message"]
        == UserResponseMessages.VERIFICATION_EMAIL_RESENT.value
    )
    assert sent_messages == []


def test_resend_verification_email_rate_limited(client):
    email = "rate-limit-verify@email.com"
    original_setting = settings.REQUIRE_EMAIL_VERIFICATION
    try:
        settings.REQUIRE_EMAIL_VERIFICATION = True
        create_response = client.post(
            "/user/create",
            json={
                "first_name": "Rate",
                "last_name": "Limited",
                "phone_number": "+27123456789",
            },
            headers=get_basic_auth_header(email, "verifyPass123"),
        )
        assert create_response.status_code == 201

        for _ in range(5):
            response = client.post("/user/resend-verification", json={"email": email})
            assert response.status_code == 200

        rate_limited_response = client.post(
            "/user/resend-verification",
            json={"email": email},
        )

        assert rate_limited_response.status_code == 429
        detail = rate_limited_response.json()["detail"]
        assert detail["message"] == UserResponseMessages.VERIFICATION_RATE_LIMITED.value
        assert detail["error"] == "verification_email_rate_limited"
    finally:
        settings.REQUIRE_EMAIL_VERIFICATION = original_setting


def test_resend_verification_email_short_circuits_when_verification_disabled(
    client, monkeypatch
):
    sent_messages = []
    monkeypatch.setattr(settings, "REQUIRE_EMAIL_VERIFICATION", False)
    monkeypatch.setattr(
        "app.services.user.verification.MailService.send_template_email",
        lambda **kwargs: sent_messages.append(kwargs),
    )

    response = client.post(
        "/user/resend-verification",
        json={"email": "disabled@example.com"},
    )

    assert response.status_code == 200
    assert response.json()["message"] == UserResponseMessages.VERIFICATION_EMAIL_RESENT.value
    assert sent_messages == []
