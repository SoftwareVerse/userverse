from app.models.user.response_messages import (
    UserResponseMessages,
    PasswordResetResponseMessages,
)


def test_password_reset_success(client, test_user_data):
    """Test password reset with valid user email"""
    user = test_user_data["user_two"]

    response = client.patch(
        "password-reset/request",
        json={"email": user["email"]},
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
        "password-reset/request",
        json={"email": unknown_email},
    )

    assert response.status_code in [400, 404]
    json_data = response.json()

    assert "detail" in json_data
    detail = json_data["detail"]

    assert "message" in detail
    assert detail["message"] == UserResponseMessages.USER_NOT_FOUND.value

    assert "error" in detail
