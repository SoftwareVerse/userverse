import pytest

from app.models.user.response_messages import PasswordResetResponseMessages
from app.utils.rate_limiter import PASSWORD_RESET_RATE_LIMITER


@pytest.fixture(autouse=True)
def reset_password_reset_rate_limiters():
    PASSWORD_RESET_RATE_LIMITER.reset()
    yield
    PASSWORD_RESET_RATE_LIMITER.reset()


def test_password_reset_success(client, test_user_data):
    """Test password reset with valid user email"""
    user = test_user_data["user_two"]

    response = client.patch(
        "password-reset/request?email=" + user["email"],
    )

    assert response.status_code in [200, 201, 202]
    json_data = response.json()

    assert "message" in json_data
    assert json_data["message"] == PasswordResetResponseMessages.OTP_SENT.value

    assert "data" in json_data
    assert json_data["data"] is None


def test_password_reset_user_not_found(client):
    """Test password reset with unknown email"""
    unknown_email = "unknown@example.com"

    response = client.patch(
        "password-reset/request?email=" + unknown_email,
    )

    assert response.status_code in [200, 201, 202]
    json_data = response.json()

    assert json_data["message"] == PasswordResetResponseMessages.OTP_SENT.value
    assert json_data["data"] is None


def test_password_reset_rate_limited(client, test_user_data):
    user = test_user_data["user_two"]

    success_responses = []
    for _ in range(5):
        response = client.patch(
            "password-reset/request?email=" + user["email"],
        )
        success_responses.append(response)

    for resp in success_responses:
        assert resp.status_code == 202

    rate_limited_response = client.patch(
        "password-reset/request?email=" + user["email"],
    )

    assert rate_limited_response.status_code == 429
    detail = rate_limited_response.json()["detail"]
    assert (
        detail["message"]
        == PasswordResetResponseMessages.RATE_LIMITED.value
    )
    assert detail["error"] == "password_reset_rate_limited"
