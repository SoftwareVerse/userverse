from app.models.user.response_messages import PasswordResetResponseMessages
from app.repository.database.session_manager import DatabaseSessionManager
from app.repository.database.tables import User
from app.utils.hash_password import verify_password


def test_a_password_reset_with_magic_link_success(
    client, test_user_data, seed_verified_users, get_user_two_otp
):
    user = test_user_data["user_two"]
    new_password = "ResetViaMagic123!"

    request_response = client.patch(
        "password-reset/request",
        json={"email": user["email"], "method": "magic_link"},
    )
    assert request_response.status_code == 202
    token = get_user_two_otp()

    response = client.patch(
        "password-reset/reset-with-token",
        json={"token": token, "new_password": new_password},
    )

    assert response.status_code == 202
    assert response.json()["message"] == PasswordResetResponseMessages.PASSWORD_CHANGED.value

    db = DatabaseSessionManager()
    session = db.session_object()
    try:
        user_row = session.query(User).filter_by(email=user["email"]).one()
        assert verify_password(new_password, user_row.password) is True
        assert "password_reset" not in (user_row.primary_meta_data or {})
    finally:
        session.close()


def test_b_password_reset_with_magic_link_invalid_token(client):
    response = client.patch(
        "password-reset/reset-with-token",
        json={"token": "invalid-token", "new_password": "ResetViaMagic123!"},
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert (
        detail["message"]
        == PasswordResetResponseMessages.MAGIC_LINK_VERIFICATION_FAILED.value
    )
    assert detail["error"] == PasswordResetResponseMessages.TOKEN_ERROR.value


def test_c_password_reset_with_magic_link_rejects_otp_token(
    client, test_user_data, seed_verified_users, get_user_two_otp
):
    user = test_user_data["user_two"]

    client.patch("password-reset/request", json={"email": user["email"]})
    otp = get_user_two_otp()

    response = client.patch(
        "password-reset/reset-with-token",
        json={"token": otp, "new_password": "ResetViaMagic123!"},
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"]["message"]
        == PasswordResetResponseMessages.MAGIC_LINK_VERIFICATION_FAILED.value
    )
