from app.models.user.response_messages import PasswordResetResponseMessages
from app.repository.database.session_manager import DatabaseSessionManager
from app.repository.database.tables import User
from app.utils.hash_password import verify_password
from tests.utils.basic_auth import get_basic_auth_header


def test_a_password_reset_validate_otp_fail(
    client, test_user_data, seed_verified_users, get_user_two_otp
):
    """Test password reset with valid user email"""
    user_one = test_user_data["user_two"]
    new_password = "NewPassword123"

    client.patch("password-reset/request?email=" + user_one["email"])

    headers = get_basic_auth_header(
        username=user_one["email"],
        password=new_password,
    )

    response = client.patch(
        f"password-reset/validate-otp?one_time_pin={get_user_two_otp}FGWSE",
        headers=headers,
    )

    assert response.status_code in [400, 401, 402]
    json_data = response.json()

    assert "detail" in json_data
    assert (
        json_data["detail"]["message"]
        == PasswordResetResponseMessages.OTP_VERIFICATION_FAILED.value
    )
    assert json_data["detail"]["error"] == PasswordResetResponseMessages.ERROR.value


def test_b_password_reset_validate_otp_success(
    client, test_user_data, seed_verified_users, get_user_two_otp
):
    """Test password reset with valid user email"""
    user_one = test_user_data["user_two"]
    new_password = "NewPassword123!"

    client.patch("password-reset/request?email=" + user_one["email"])
    otp = get_user_two_otp()

    headers = get_basic_auth_header(
        username=user_one["email"],
        password=new_password,
    )

    response = client.patch(
        f"password-reset/validate-otp?one_time_pin={otp}",
        headers=headers,
    )

    assert response.status_code in [200, 201, 202]
    json_data = response.json()

    assert "message" in json_data
    assert json_data["message"] == PasswordResetResponseMessages.PASSWORD_CHANGED.value

    assert "data" in json_data
    assert json_data["data"] is None

    db = DatabaseSessionManager()
    session = db.session_object()
    try:
        user_row = session.query(User).filter_by(email=user_one["email"]).one()
        assert user_row.password != new_password
        assert verify_password(new_password, user_row.password) is True
        assert "password_reset" not in (user_row.primary_meta_data or {})
    finally:
        session.close()
