import pytest

from app.models.user.password import PasswordResetMethod
from app.models.user.response_messages import PasswordResetResponseMessages
from app.repository.database.session_manager import DatabaseSessionManager
from app.repository.database.tables import User
from app.utils.rate_limiter import PASSWORD_RESET_RATE_LIMITER



pytestmark = pytest.mark.anyio
@pytest.fixture(autouse=True)
def reset_password_reset_rate_limiters():
    PASSWORD_RESET_RATE_LIMITER.reset()
    yield
    PASSWORD_RESET_RATE_LIMITER.reset()


async def test_password_reset_success(client, test_user_data, seed_users):
    """Test password reset with valid user email"""
    user = test_user_data["user_two"]

    response = await client.patch(
        "password-reset/request",
        json={"email": user["email"]},
    )

    assert response.status_code in [200, 201, 202]
    json_data = response.json()

    assert "message" in json_data
    assert json_data["message"] == PasswordResetResponseMessages.OTP_SENT.value

    assert "data" in json_data
    assert json_data["data"] is None

    db = DatabaseSessionManager()
    session = db.session_object()
    try:
        user_row = session.query(User).filter_by(email=user["email"]).one()
        password_reset = (user_row.primary_meta_data or {}).get("password_reset", {})
        assert password_reset["method"] == PasswordResetMethod.OTP.value
        assert password_reset["token"]
        assert password_reset["created_at"]
        assert password_reset["expires_at"]
    finally:
        session.close()


async def test_password_reset_magic_link_success(client, test_user_data, seed_users):
    user = test_user_data["user_two"]

    response = await client.patch(
        "password-reset/request",
        json={"email": user["email"], "method": "magic_link"},
    )

    assert response.status_code == 202
    json_data = response.json()
    assert json_data["message"] == PasswordResetResponseMessages.OTP_SENT.value

    db = DatabaseSessionManager()
    session = db.session_object()
    try:
        user_row = session.query(User).filter_by(email=user["email"]).one()
        password_reset = (user_row.primary_meta_data or {}).get("password_reset", {})
        assert password_reset["method"] == PasswordResetMethod.MAGIC_LINK.value
        assert password_reset["token"]
        assert password_reset["created_at"]
        assert password_reset["expires_at"]
    finally:
        session.close()


async def test_password_reset_user_not_found(client):
    """Test password reset with unknown email"""
    unknown_email = "unknown@example.com"

    response = await client.patch(
        "password-reset/request",
        json={"email": unknown_email},
    )

    assert response.status_code in [200, 201, 202]
    json_data = response.json()

    assert json_data["message"] == PasswordResetResponseMessages.OTP_SENT.value
    assert json_data["data"] is None


async def test_password_reset_rate_limited(client, test_user_data, seed_users):
    user = test_user_data["user_two"]

    success_responses = []
    for _ in range(5):
        response = await client.patch(
            "password-reset/request",
            json={"email": user["email"]},
        )
        success_responses.append(response)

    for resp in success_responses:
        assert resp.status_code == 202

    rate_limited_response = await client.patch(
        "password-reset/request",
        json={"email": user["email"]},
    )

    assert rate_limited_response.status_code == 429
    detail = rate_limited_response.json()["detail"]
    assert detail["message"] == PasswordResetResponseMessages.RATE_LIMITED.value
    assert detail["error"] == "password_reset_rate_limited"


async def test_password_reset_magic_link_requires_frontend_url(
    client, test_user_data, seed_users, monkeypatch
):
    user = test_user_data["user_two"]
    monkeypatch.setattr("app.services.user.password.settings.FRONTEND_URL", None)

    response = await client.patch(
        "password-reset/request",
        json={"email": user["email"], "method": "magic_link"},
    )

    assert response.status_code == 500
    detail = response.json()["detail"]
    assert (
        detail["message"]
        == PasswordResetResponseMessages.FRONTEND_URL_NOT_CONFIGURED.value
    )
    assert detail["error"] == "frontend_url_not_configured"
